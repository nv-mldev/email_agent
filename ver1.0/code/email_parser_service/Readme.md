Of course. Let's visualize how the two services interact through RabbitMQ.

The `email_polling_service` acts as the **Publisher** (or Producer), and the `email_parser_service` acts as the **Consumer**. Here’s a step-by-step demonstration of what you would see on your screen when they run.

### The Setup

Imagine you have two terminal windows open.

1. **Terminal 1**: Will run the `email_parser_service` (the consumer), which will connect to RabbitMQ and wait patiently.
2. **Terminal 2**: Will run the `email_polling_service`'s script (the publisher), which will find an email and send a message.

---

### Step 1: Start the Consumer (Email Parser Service)

First, you start the service that will listen for messages.

In **Terminal 1**, you run the `email_parser_service`:

```bash
# In email_agent/ directory
python -m email_parser_service.main
```

The output in Terminal 1 will look like this. It connects to RabbitMQ and then waits, listening on the `email_parser_queue`.

```
[*] Waiting for messages on 'email_parser_queue'. To exit press CTRL+C
```

At this moment, your consumer is active and idle, waiting for a task.

---

### Step 2: An Unread Email Arrives

Now, let's say an unread email from `acme_invoices@example.com` with the subject "Invoice INV-2025-06-15" and one PDF attachment arrives in your `hello@cargoa.io` inbox.

---

### Step 3: Run the Publisher (Email Polling Service)

Next, the cron job triggers your polling script (or you run it manually for this demonstration).

In **Terminal 2**, you execute the `poll_emails.py` script:

```bash
# In email_agent/ directory
python -m email_polling_service.poll_emails
```

The script will find the new unread email and publish a message about it. The output in Terminal 2 will be:

```
--- Starting email polling cycle at 2025-06-15T18:48:10.123456 ---
Checking for unread messages...
Found 1 unread email(s). Processing...
Processing message ID: AAMkADliZTc1YjYtOD...
Successfully published message for email_id: AAMkADliZTc1YjYtOD...
Successfully marked message AAMkADliZTc1YjYtOD... as read.
Graph client resources closed.
RabbitMQ connection closed.
--- Email polling cycle finished at 2025-06-15T18:48:12.654321 ---
```

The publisher has done its job. It sent a small JSON message to the `email_parser_queue` and exited.

---

### Step 4: The Consumer Wakes Up and Works

Instantly, the consumer in **Terminal 1**, which was waiting patiently, receives the message and springs into action. Its terminal output will immediately update with the processing logs.

This is the moment the "consuming" happens.

```
[*] Waiting for messages on 'email_parser_queue'. To exit press CTRL+C

--- Processing message from queue. Graph ID: AAMkADliZTc1YjYtOD... ---
Email has attachments. Processing...
  Downloading attachment: invoice_acme_corp.pdf
Successfully uploaded 'invoice_acme_corp.pdf' to blob path: acme_invoices@example.com/long-internet-message-id/invoice_acme_corp.pdf
Successfully parsed and published results for AAMkADliZTc1YjYtOD... to 'document_identifier_queue'

```

After this burst of activity, the consumer goes back to its idle waiting state, ready for the next message:

```
[*] Waiting for messages on 'email_parser_queue'. To exit press CTRL+C
```

### Summary of the Interaction

1. **Publisher (`poll_emails.py`)**:
    * **Connects** to RabbitMQ.
    * **Sends** a message like `{"graph_message_id": "AAMk...", "has_attachments": true, ...}` to the `email_parser_queue`.
    * **Closes** its connection.

2. **Consumer (`email_parser_service`)**:
    * **Listens** constantly to the `email_parser_queue`.
    * **Receives** the message from the publisher.
    * **Performs its tasks**: uses the `graph_message_id` to download the full email and attachments, and uploads them to Azure Blob.
    * **Publishes a new, enriched message** to the *next* queue (`document_identifier_queue`) for the next service in the chain.
    * **Acknowledges** the original message, removing it from `email_parser_queue`.
    * **Goes back** to listening.

This is a classic and highly effective publisher-subscriber pattern. The services are completely decoupled; the poller doesn't know or care what happens after it sends the message, and the parser doesn't know where the message came from. They only agree on the queue name and the message format.

 email agent
Custom Gem

Excellent question. You've hit upon a critical point that moves our design from a simple pipeline to a robust, production-grade application.

Yes, absolutely. Introducing a database to store message metadata is not only a good idea, but essential for handling real-world complexities like CC'ing, ensuring reliability, and providing an audit trail.

Let's break down why this is so important and how we can implement it.
Why You Need a Database Now

    Idempotency (Preventing Duplicate Processing): What happens if the email_parser_service crashes after uploading an attachment but before acknowledging the RabbitMQ message? The message will be redelivered, and the service would process the exact same email again, creating duplicate files and downstream tasks. A database solves this. By logging the internet_message_id first, you can always check: "Have I processed this email before?"

    Handling the 'CC' Logic (Your Specific Question): You are right, the current logic processes every unread email the same way. With a database, you can implement specific business rules:
        You can fetch the To: and CC: fields from the email.
        If hello@cargoa.io is in the To: field, it's a primary task.
        If hello@cargoa.io is only in the CC: field, it might be for informational purposes. You could flag it in the database for manual review or apply a different, lower-priority workflow. Without a database, this state is lost.

    Audit Trail and Debugging: When a user asks, "What happened to the invoice I sent on Tuesday?", you can't find the answer in a temporary RabbitMQ message. A database gives you a permanent record of every email received, when it was processed, its status, and any errors that occurred.

    State Management for the UI: The UI will eventually need to show the history and status of all processed documents, not just ones pending confirmation. The database is the single source of truth for this.

How to Handle CC'd Emails

The MS Graph API query for unread mail (isRead eq false) fetches all messages in the inbox, regardless of whether your address is in the To, CC, or even BCC field. This is good news—we don't miss any emails.

The key is to fetch the recipient lists and analyze them. The Message object from Graph API contains toRecipients and ccRecipients properties, which are lists of email addresses.

Here's the new logic:

    When an email is received, fetch its toRecipients and ccRecipients.
    Check if hello@cargoa.io is in the toRecipients list.
    If not, check if it's in the ccRecipients list.
    Save this role (TO or CC) in the database. This allows all downstream services to make smarter decisions.
