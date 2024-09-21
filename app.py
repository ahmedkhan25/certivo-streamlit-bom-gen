## streamlit app to generate BOM and documents for a product using Anthropic API

import streamlit as st
import os
import json
import io
from fpdf import FPDF
from zipfile import ZipFile
from dotenv import load_dotenv
import anthropic
from anthropic import APIError

load_dotenv()  # Load environment variables from .env file

# Load your actual Anthropic API key from environment variables
ANTHROPIC_API_KEY = st.secrets['ANTHROPIC_API_KEY'] 

def call_anthropic_api(prompt):
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    try:
        message = client.messages.create(
            model="claude-3-sonnet-20240229",
            max_tokens=4000,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )
        return message.content[0].text, message.usage
    except APIError as e:
        st.error(f"API Error: {e}")
        raise
    except Exception as e:
        st.error(f"Unexpected error in API call: {e}")
        raise

def generate_csv_from_response(response_text):
    csv_buffer = io.StringIO(response_text)
    csv_file = io.BytesIO()
    csv_file.write(csv_buffer.getvalue().encode('utf-8'))
    csv_file.seek(0)
    return csv_file

def generate_pdf_from_response(response_text):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    lines = response_text.strip().split('\n')
    for line in lines:
        pdf.cell(200, 10, txt=line.encode('latin-1', 'replace').decode('latin-1'), ln=True)
    pdf_content = pdf.output(dest='S').encode('latin-1')
    return pdf_content

def get_parts_from_bom(bom_response):
    try:
        parts = json.loads(bom_response)
        return parts
    except json.JSONDecodeError as e:
        st.error(f"Error decoding JSON: {str(e)}")
        return []

# Streamlit app
st.set_page_config(page_title="BOM Generator", page_icon="📋")

# Add logo
st.image("https://framerusercontent.com/images/JrOd61Z55WJibdnT1hT9QZ0Zk6U.png", width=200)  # Replace with your actual logo URL

st.title("BOM Generator")

st.markdown("""
This tool generates the following files:
1. Bill of Materials (BOM) in CSV format
2. Material Specification Sheet in PDF format
3. Product Compliance Certificates for each part in PDF format
4. Approved Vendor List in PDF format

All files are packaged into a single ZIP file for easy download.
""")

# User inputs with examples
industry = st.selectbox("Industry", 
    ["Electronics", "Automotive", "Medical Devices", "Consumer Goods", "Textiles", "Chemicals"],
    help="Select the industry for your product")

product_examples = {
    "Electronics": "Smartwatch",
    "Automotive": "Electric Scooter",
    "Medical Devices": "Digital Thermometer",
    "Consumer Goods": "Toy Car",
    "Textiles": "Baseball Cap",
    "Chemicals": "Plastic Water Bottle"
}

product_type = st.text_input("Type of Product", 
    placeholder=f"E.g., {product_examples.get(industry, 'Smartwatch')}",
    help="Enter the specific type of product you're creating a BOM for")

number_of_parts = st.number_input("Number of Parts", min_value=1, max_value=25, value=5,
    help="Enter the number of top-level parts in your BOM (max 25)")

number_of_nested_parts = st.number_input("Number of Nested Parts", min_value=0, max_value=3, value=1,
    help="Enter the number of nested levels (max 3). This represents subproducts within your main product.")

if st.button("Generate BOM and Documents"):
    if not all([industry, product_type, number_of_parts, number_of_nested_parts]):
        st.error("All input fields are required.")
        st.stop()

    progress_bar = st.progress(0)
    status_text = st.empty()
    total_input_tokens = 0
    total_output_tokens = 0

    # Step A: Generating BOM
    status_text.text("Generating BOM...")
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

    bom_response, bom_usage = call_anthropic_api(bom_prompt)
    total_input_tokens += bom_usage.input_tokens
    total_output_tokens += bom_usage.output_tokens
    
    # Split the response into CSV and JSON parts
    csv_content, json_content = bom_response.split('JSON:', 1)
    csv_content = csv_content.replace('CSV:', '').strip()
    json_content = json_content.strip()

    bom_csv = generate_csv_from_response(csv_content)
    parts = get_parts_from_bom(json_content)
    progress_bar.progress(25)

    # Step B: Generating Material Specification Sheet
    status_text.text("Generating Material Specification Sheet...")
    compliance_prompt = f"""Using the following BOM data:

{csv_content}

Create a hypothetical material specification sheet for the {product_type} in the {industry} industry. Include:
1. A breakdown of materials used in the product, with percentages.
2. Specific material names and their properties.
3. Compliance status with relevant standards (e.g., RoHS, REACH).
4. Any special handling or disposal considerations.
5. Reference the vendors or manufacturers from the BOM where appropriate.
Provide only the content of the material specification sheet, no additional commentary."""

    compliance_response, compliance_usage = call_anthropic_api(compliance_prompt)
    total_input_tokens += compliance_usage.input_tokens
    total_output_tokens += compliance_usage.output_tokens
    compliance_pdf = generate_pdf_from_response(compliance_response)
    progress_bar.progress(50)

    # Step C: Generating Product Compliance Certificates
    status_text.text("Generating Product Compliance Certificates...")
    if not parts:
        st.error("No parts extracted from BOM")
        st.stop()

    certs = []
    for i, part in enumerate(parts):
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

        cert_response, cert_usage = call_anthropic_api(cert_prompt)
        total_input_tokens += cert_usage.input_tokens
        total_output_tokens += cert_usage.output_tokens
        cert_pdf = generate_pdf_from_response(cert_response)
        certs.append({'filename': f"Compliance_Cert_{part['part_number']}.pdf", 'file': cert_pdf})
        progress_bar.progress(50 + (i + 1) * 25 // len(parts))

    # Step D: Generating Approved Vendor List
    status_text.text("Generating Approved Vendor List...")
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

    vendors_response, vendors_usage = call_anthropic_api(vendors_prompt)
    total_input_tokens += vendors_usage.input_tokens
    total_output_tokens += vendors_usage.output_tokens
    vendors_pdf = generate_pdf_from_response(vendors_response)
    progress_bar.progress(100)

    # Create ZIP file
    status_text.text("Creating ZIP file...")
    zip_buffer = io.BytesIO()
    with ZipFile(zip_buffer, 'w') as zip_file:
        zip_file.writestr('BOM.csv', bom_csv.getvalue())
        zip_file.writestr('Material_Specification_Sheet.pdf', compliance_pdf)
        zip_file.writestr('Approved_Vendors.pdf', vendors_pdf)
        for cert in certs:
            zip_file.writestr(cert['filename'], cert['file'])
    zip_buffer.seek(0)

    # Offer ZIP file for download
    st.download_button(
        label="Download ZIP file",
        data=zip_buffer,
        file_name="output_files.zip",
        mime="application/zip"
    )

    status_text.text("Generation complete!")
    st.success(f"Total tokens used: Input: {total_input_tokens}, Output: {total_output_tokens}")



if __name__ == "__main__":
    st.write("BOM Generator is ready to use.")