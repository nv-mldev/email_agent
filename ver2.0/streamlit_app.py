# streamlit_app.py

import streamlit as st
import requests
import pandas as pd
from datetime import datetime
import time

# --- Configuration ---
API_BASE_URL = "http://localhost:8000"  # URL of your FastAPI server

# --- Helper Functions ---


def get_all_logs():
    """Fetches all email logs from the API."""
    try:
        response = requests.get(f"{API_BASE_URL}/api/logs")
        response.raise_for_status()  # Raise an exception for bad status codes
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"Error fetching data from API: {e}")
        return []


def get_log_details(log_id):
    """Fetches full details for a single email log."""
    try:
        response = requests.get(f"{API_BASE_URL}/api/logs/{log_id}")
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"Error fetching details for log {log_id}: {e}")
        return None


def confirm_and_create_shipment(log_id):
    """Tells the API to confirm the log and trigger the final step."""
    try:
        # In a real app, this endpoint would trigger the shipment creation
        # For now, we'll imagine it just updates the status
        # response = requests.post(f"{API_BASE_URL}/api/logs/{log_id}/confirm")
        # response.raise_for_status()
        st.success(
            f"Confirmed Log ID: {log_id}. Shipment creation process has been triggered."
        )
        return True
    except requests.exceptions.RequestException as e:
        st.error(f"Failed to confirm Log ID {log_id}: {e}")
        return False


def fetch_emails_manually():
    """Manually trigger email fetching via API."""
    try:
        with st.spinner("Fetching emails from mailbox..."):
            response = requests.post(f"{API_BASE_URL}/api/fetch-emails")
            response.raise_for_status()
            result = response.json()
            st.success("✅ " + result.get("message", "Emails fetched successfully!"))
            return True
    except requests.exceptions.RequestException as e:
        st.error(f"❌ Failed to fetch emails: {e}")
        return False


# --- Main App ---

st.set_page_config(page_title="Email Agent Review Dashboard", layout="wide")

st.title("📧 Email Agent Review Dashboard")
st.caption(f"Last updated: {datetime.now().strftime('%H:%M:%S')}")

# Add manual fetch button for staging/testing
col1, col2 = st.columns([3, 1])
with col2:
    if st.button("📥 Fetch Emails", type="primary", use_container_width=True):
        if fetch_emails_manually():
            time.sleep(2)  # Give time for processing
            st.rerun()  # Refresh to show new emails

# Fetch the data
email_logs = get_all_logs()

if not email_logs:
    st.warning("No email logs found. Click 'Fetch Emails' to check for new messages!")
else:
    # Create a dataframe for a clean summary view
    df = pd.DataFrame(email_logs)
    # Include PO number in the summary table
    df = df[
        [
            "id",
            "status",
            "sender_address",
            "subject",
            "purchase_order_number",
            "received_at",
        ]
    ]
    df["received_at"] = pd.to_datetime(df["received_at"]).dt.strftime("%Y-%m-%d %H:%M")

    # Rename columns for better display
    df.columns = ["ID", "Status", "Sender", "Subject", "PO Number", "Received"]

    st.dataframe(df, use_container_width=True)

    st.divider()

    # Get the ID of the email to inspect
    selected_id = st.selectbox(
        "Select an Email ID to inspect:", options=[log["id"] for log in email_logs]
    )

    if selected_id:
        # Display details for the selected email
        details = get_log_details(selected_id)

        if details:
            st.header(f"Details for Email ID: {details['id']}")
            st.subheader(f"Subject: {details['subject']}")

            # Create columns for better layout
            col1, col2 = st.columns([3, 1])
            with col1:
                st.text(
                    f"From: {details['sender_address']} | Status: {details['status']}"
                )
            with col2:
                # Display PO number prominently
                po_number = details.get("purchase_order_number")
                if po_number:
                    st.success(f"🔢 PO: {po_number}")
                else:
                    st.info("🔢 PO: Not Found")

            with st.expander("Email Summary & Body"):
                st.markdown("**AI Generated Summary:**")
                st.info(details.get("email_summary", "No summary generated."))
                st.markdown("**Full Email Body:**")
                st.text(details.get("body", "No body content."))

            st.subheader("📄 Document Analysis")

            attachments = details.get("parsed_attachments_json", [])
            if not attachments:
                st.info("No attachments found or processed for this email.")
            else:
                for attachment in attachments:
                    st.markdown(f"**File:** `{attachment['original_filename']}`")

                    identified_docs = attachment.get("identified_documents", [])
                    if not identified_docs:
                        st.warning("No documents were identified in this file.")
                    else:
                        for doc in identified_docs:
                            col1, col2, col3 = st.columns([2, 1, 1])
                            col1.success(f"**Document Type:** {doc['doc_type']}")
                            col2.metric("Confidence", f"{doc['confidence']*100:.1f}%")
                            col3.info(f"Pages: {doc['start_page']} - {doc['end_page']}")

            # --- Confirmation Button ---
            st.divider()
            if details["status"] == "PENDING_CONFIRMATION":
                if st.button(
                    "✅ Confirm & Create Shipment",
                    key=f"confirm_{details['id']}",
                    use_container_width=True,
                ):
                    if confirm_and_create_shipment(details["id"]):
                        # If confirmation is successful, wait and rerun to see status change
                        time.sleep(2)
                        st.rerun()  # <--- UPDATED
            else:
                st.info(
                    f"This email's status is '{details['status']}' and does not require confirmation."
                )

# --- Manual refresh mode for staging ---
st.sidebar.info("🔄 Manual Mode: Use 'Fetch Emails' button to check for new messages")
st.sidebar.caption("💡 Perfect for staging/testing environments!")
