#hosted on pythonanywhere.com
#user accout: ahmed25
#email: ahmed@certivo.com
#password: b%VFF(*^qzwN$7r

from flask import Flask, request, send_file, jsonify
import os
import json
import io
from fpdf import FPDF
from zipfile import ZipFile
from dotenv import load_dotenv
import anthropic
from anthropic import APIError

load_dotenv()  # Load environment variables from .env file

app = Flask(__name__)

# Load your actual Anthropic API key from environment variables
ANTHROPIC_API_KEY = os.getenv('ANTHROPIC_API_KEY')

def call_anthropic_api(prompt):
    print(f"Calling Anthropic API with prompt: {prompt[:50]}...")  # Debug print
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    try:
        message = client.messages.create(
            model="claude-3-sonnet-20240229",
            max_tokens=4000,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )
        print("API call successful")  # Debug print
        return message.content[0].text
    except APIError as e:
        print(f"API Error: {e}")
        print(f"Error details: {e.response.json()}")
        raise
    except Exception as e:
        print(f"Unexpected error in API call: {e}")
        raise

def generate_csv_from_response(response_text):
    print("Generating CSV from response")  # Debug print
    csv_buffer = io.StringIO(response_text)
    csv_file = io.BytesIO()
    csv_file.write(csv_buffer.getvalue().encode('utf-8'))
    csv_file.seek(0)
    print("CSV generation complete")  # Debug print
    return csv_file

def generate_pdf_from_response(response_text):
    print("Generating PDF from response")  # Debug print
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    lines = response_text.strip().split('\n')
    for line in lines:
        pdf.cell(200, 10, txt=line.encode('latin-1', 'replace').decode('latin-1'), ln=True)
    pdf_content = pdf.output(dest='S').encode('latin-1')
    print("PDF generation complete")  # Debug print
    return pdf_content

def get_parts_from_bom(bom_response):
    print("Extracting parts from BOM")  # Debug print
    try:
        parts = json.loads(bom_response)
        print(f"Extracted {len(parts)} parts from BOM")  # Debug print
        if len(parts) > 0:
            print(f"First few parts: {parts[:5]}")  # Debug print
        else:
            print("No parts extracted from BOM")
        return parts
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON: {str(e)}")
        return []

@app.route('/generate', methods=['POST'])
def generate():
    try:
        print("Starting generate function")  # Debug print
        data = request.get_json()
        industry = data.get('industry')
        product_type = data.get('type_of_product')
        number_of_parts = data.get('number_of_parts')
        number_of_nested_parts = data.get('number_of_nested_parts')

        # Input validation
        if not all([industry, product_type, number_of_parts, number_of_nested_parts]):
            print("Input validation failed")  # Debug print
            return jsonify({'error': 'All input fields are required.'}), 400

        print("Step A: Generating BOM")  # Debug print
        bom_example = """BOM Part Number,SONY-WH-1000XM5,,,,,,,,,,,,,,,,,,,,
BOM Name,Sony WH-1000XM5 Wireless Noise-Canceling Headphones Manufacturing BOM,,,,,,,,,,,,,,,,,,,,
Date,15 Sep 2024; 10:30:15 GMT,,,,,,,,,,,,,,,,,,,,
Last update by user,productmanager@sony.com,,,,,,,,,,,,,,,,,,,,
Created by user,engineeringlead@sony.com,,,,,,,,,,,,,,,,,,,,
Revision,1.0,,,,,,,,,,,,,,,,,,,,
,,,,,,,,,,,,,,,,,,,,,
Part Number,Thumbnail image,Quantity,Total Cost,Vendor,Description,Cost,Quantity On Hand,Unit,Inventory Cost,Date created,Date saved,Drawing File in GoogleDrive,File Name,Saved by,Configuration Name,CAD File in GoogleDrive,3DView File,Type,2D PDF File in GoogleDrive,Material,Compliance Notes
HP-DRIVER-40,,2,$ 30.00,Sony Audio,40mm Dynamic Driver,$ 15.00,500,Each,$ 7500.00,1/5/2024 9:00:00 AM,15/9/2024 10:30:15 AM,HP-DRIVER-40.pdf,HP-DRIVER-40.SLDPRT,engineeringlead,Default,HP-DRIVER-40.SLDPRT,HP-DRIVER-40.SLDPRT,Part,HP-DRIVER-40.SLDPRT.2D.pdf,Neodymium/Aluminum,RoHS compliant
HP-BT-CHIP,,1,$ 20.00,Qualcomm,Bluetooth 5.2 Chip,$ 20.00,1000,Each,$ 20000.00,1/6/2024 10:30:00 AM,15/9/2024 10:30:15 AM,HP-BT-CHIP.pdf,HP-BT-CHIP.SLDPRT,engineeringlead,Default,HP-BT-CHIP.SLDPRT,HP-BT-CHIP.SLDPRT,Part,HP-BT-CHIP.SLDPRT.2D.pdf,Silicon,RoHS compliant; REACH status pending"""

        bom_prompt = f"""Generate a CSV file for a Bill of Materials (BOM) for an {industry} product of type '{product_type}', with {number_of_parts} parts and {number_of_nested_parts} nested parts. Use the following example as a reference for the format:

{bom_example}

Include the following:
1. Metadata rows at the top with BOM Part Number, BOM Name, Date, Last update by user, Created by user, and Revision.
2. A header row with these columns: Part Number, Quantity, Total Cost, Vendor, Description, Cost, Quantity On Hand, Unit, Inventory Cost, Material, Compliance Notes.
3. {number_of_parts} rows of part data, each with a unique part number (use a realistic format, not just 'Part 1', 'Part 2', etc.), realistic quantities, costs, and 3-4 hypothetical vendor names.
4. Ensure compliance notes mention RoHS, REACH, or other relevant standards.

After generating the CSV, create a JSON array of part objects. Each object should have 'part_number' and 'description' properties. Include the BOM itself as the first item in this array.

Return your response in the following format:
CSV:
[Your generated CSV content here]

JSON:
[Your JSON array of part objects here]

Only provide the CSV content and JSON array as specified, no additional explanation."""

        bom_response = call_anthropic_api(bom_prompt)
        
        # Split the response into CSV and JSON parts
        csv_content, json_content = bom_response.split('JSON:', 1)
        csv_content = csv_content.replace('CSV:', '').strip()
        json_content = json_content.strip()

        bom_csv = generate_csv_from_response(csv_content)
        parts = get_parts_from_bom(json_content)
        print("BOM generation complete")  # Debug print

        print("Step B: Generating Material Specification Sheet")  # Debug print
        compliance_prompt = f"""Using the following BOM data:

{csv_content}

Create a hypothetical material specification sheet for the {product_type} in the {industry} industry. Include:
1. A breakdown of materials used in the product, with percentages.
2. Specific material names and their properties.
3. Compliance status with relevant standards (e.g., RoHS, REACH).
4. Any special handling or disposal considerations.
5. Reference the vendors or manufacturers from the BOM where appropriate.
Provide only the content of the material specification sheet, no additional commentary."""

        compliance_response = call_anthropic_api(compliance_prompt)
        compliance_pdf = generate_pdf_from_response(compliance_response)
        print("Material Specification Sheet generation complete")  # Debug print

        print("Step C: Generating Product Compliance Certificates")  # Debug print
        
        if not parts:
            raise ValueError("No parts extracted from BOM")
        
        certs = []
        for part in parts:
            print(f"Generating certificate for part: {part['part_number']}")  # Debug print
            cert_prompt = f"""Using the following BOM data:

{csv_content}

Create a product compliance certificate for part number '{part['part_number']}' (Description: {part['description']}) in the BOM for the {product_type}. Include:
1. Part number and description (use the exact part number and description provided)
2. Vendor name (use the vendor name from the BOM if available)
3. Applicable standards (e.g., RoHS, REACH, CE)
4. Compliance status
5. Testing information (dates, methods)
6. Authorized signatory
Provide only the certificate content, no additional explanation."""

            cert_response = call_anthropic_api(cert_prompt)
            cert_pdf = generate_pdf_from_response(cert_response)
            certs.append({'filename': f"Compliance_Cert_{part['part_number']}.pdf", 'file': cert_pdf})
        print("Product Compliance Certificates generation complete")  # Debug print

        print("Step D: Generating Approved Vendor List")  # Debug print
        vendors_prompt = f"""Using the following BOM data:

{csv_content}

Create an approved vendor list based on the vendors mentioned in the BOM for the {product_type}. For each unique vendor in the BOM, provide:
1. Vendor name (use the exact names from the BOM)
2. Contact person's name (invent a realistic name)
3. Email address (invent a plausible email based on the vendor name)
4. Physical address (invent a realistic address)
5. Phone number
6. Parts supplied (list the specific parts from the BOM that this vendor supplies)
Provide only the vendor list content in a clear, organized format. Do not include any additional commentary or explanations."""

        vendors_response = call_anthropic_api(vendors_prompt)
        vendors_pdf = generate_pdf_from_response(vendors_response)
        print("Approved Vendor List generation complete")  # Debug print

        print("Creating ZIP archive")  # Debug print
        zip_buffer = io.BytesIO()
        with ZipFile(zip_buffer, 'w') as zip_file:
            print("Adding BOM to ZIP")  # Debug print
            zip_file.writestr('BOM.csv', bom_csv.getvalue())
            print("Adding Material Specification Sheet to ZIP")  # Debug print
            zip_file.writestr('Material_Specification_Sheet.pdf', compliance_pdf)
            print("Adding Approved Vendors to ZIP")  # Debug print
            zip_file.writestr('Approved_Vendors.pdf', vendors_pdf)
            for cert in certs:
                print(f"Adding certificate for {cert['filename']} to ZIP")  # Debug print
                zip_file.writestr(cert['filename'], cert['file'])
        zip_buffer.seek(0)
        print("ZIP archive creation complete")  # Debug print

        print("Sending file")  # Debug print
        return send_file(
            zip_buffer,
            mimetype='application/zip',
            as_attachment=True,
            download_name='output_files.zip'
        )

    except Exception as e:
        print(f"Error in generate function: {str(e)}")  # Debug print
        import traceback
        traceback.print_exc()  # Print full traceback
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)