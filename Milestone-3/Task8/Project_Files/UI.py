import os
import streamlit as st
from streamlit_tags import st_tags
from datetime import datetime
from io import BytesIO
from scraper import perform_scrape
from tools import html_to_markdown_with_readability
import pandas as pd
# Add custom CSS for table styling
CUSTOM_CSS = """
<style>
    .table-container {
        display: flex;
        justify-content: center;
        margin: 2rem auto;
        max-width: 90%;
    }
    .stDataFrame {
        width: 100%;
    }
    .dataframe {
        margin: 0 auto;
    }
</style>
"""

def main():
    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

    # Main title with centered alignment
    st.markdown("<h1 style='text-align: center;'>Universal Web Scraper 🐙</h1>", unsafe_allow_html=True)
    tr=False
    # Sidebar for settings
    with st.sidebar:
        st.header("Web Scraper Settings")
        
        model = st.selectbox("Select Model", ["gemini flash-1.5"])
        url = st.text_input("Enter URL")
        
        # Tag input for fields to extract
        fields_to_extract = st_tags(
            label="Fields to Extract",
            text="Press enter to add a tag",
            value=st.session_state.fields,
            suggestions=[],
            key="field_tags"
        )
        
        # Prevent duplicate tags
        unique_fields = []
        for field in fields_to_extract:
            if field not in unique_fields:
                unique_fields.append(field)
        st.session_state.fields = unique_fields
        tr=st.button("Scrape")
        
    if tr :
            if not url:
                st.error("Please enter a URL")
                st.stop()
                
            if not unique_fields:
                st.error("Please enter at least one field to extract")
                st.stop()
                
            try:
                # Assuming perform_scrape is a function that returns the required data
                df, input_tokens, output_tokens, total_cost = perform_scrape(url, unique_fields, model)
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                if len(df) > 0:
                    st.success(f"Successfully extracted {len(df)} entries!")
                    
                    # Centered output table with custom styling
                    st.markdown("<div style='display: flex; justify-content: center; flex-direction: column; align-items: center;'>", unsafe_allow_html=True)
                    st.markdown("<h2 style='text-align: center;'>Extracted Data</h2>", unsafe_allow_html=True)
                    st.markdown("<div class='table-container' style='width: 100%; max-width: 800px;'>", unsafe_allow_html=True)
                    st.dataframe(df, use_container_width=True)
                    st.markdown("</div>", unsafe_allow_html=True)
                    
                    # Centered download buttons
                    st.markdown("<div style='display: flex; justify-content: center; gap: 1rem; width: 100%; max-width: 800px;'>", unsafe_allow_html=True)
                    
                    csv = df.to_csv(index=False)
                    st.download_button(
                        label="Download Data as CSV",
                        data=csv,
                        file_name=f"scraped_data_{timestamp}.csv",
                        mime="text/csv"
                    )
                    
                    output = BytesIO()
                    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                        df.to_excel(writer, index=False, sheet_name="ScrapedData")
                    xlsx_data = output.getvalue()
                    
                    st.download_button(
                        label="Download Data as XLSX",
                        data=xlsx_data,
                        file_name=f"scraped_data_{timestamp}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
                    
                    markdown = df.to_markdown(index=False)
                    st.download_button(
                        label="Download Data as Markdown",
                        data=markdown,
                        file_name=f"scraped_data_{timestamp}.md",
                        mime="text/markdown"
                    )
                    
                    json_data = df.to_json(orient="records")
                    st.download_button(
                        label="Download Data as JSON",
                        data=json_data,
                        file_name=f"scraped_data_{timestamp}.json",
                        mime="application/json"
                    )
                    
                    st.markdown("</div>", unsafe_allow_html=True)
                    st.markdown("</div>", unsafe_allow_html=True)
                with st.sidebar:
                    col1, col2, col3 = st.sidebar.columns(3)
                    with col1:
                        st.metric("Input Tokens", input_tokens)
                    with col2:
                        st.metric("Output Tokens", output_tokens)
                    with col3:
                        st.metric("Total Tokens", input_tokens + output_tokens)
                    
            except Exception as e:
                st.error(f"Error during scraping: {str(e)}")

if __name__ == "__main__":
    if 'fields' not in st.session_state:
        st.session_state.fields = []
    main()