import streamlit as st


def render_sidebar():
    st.sidebar.title("Navigation")
    st.sidebar.page_link("main.py", label="Home")
    st.sidebar.page_link("pages/1_📄_Document_Upload.py", label="Document Upload")
    st.sidebar.page_link("pages/2_🔍_Query_Interface.py", label="Query Interface")
    st.sidebar.page_link("pages/3_📊_Data_Store_Viewer.py", label="Data Store Viewer")
    st.sidebar.page_link("pages/4_🕸️_Document_Graph.py", label="Document Graph")
    st.sidebar.page_link("pages/5_⚙️_Settings.py", label="Settings")
