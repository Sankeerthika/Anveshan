import os
import smtplib
from email.mime.text import MIMEText
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

def test_smtp():
    host = os.getenv("SMTP_HOST")
    port = os.getenv("SMTP_PORT")
    user = os.getenv("SMTP_USER")
    password = os.getenv("SMTP_PASSWORD")
    tls = os.getenv("SMTP_TLS", "true").lower() == "true"

    print(f"Configuration:")
    print(f"  Host: {host}")
    print(f"  Port: {port}")
    print(f"  User: {user}")
    print(f"  Password: {'*' * len(password) if password else 'None'}")
    print(f"  TLS: {tls}")
    print("-" * 20)

    if not user or "your_email" in user:
        print("❌ ERROR: It looks like you are still using placeholder credentials in .env")
        print("Please update d:\\anveshan\\.env with your real email and app password.")
        return

    try:
        print("Attempting to connect to SMTP server...")
        server = smtplib.SMTP(host, int(port))
        server.set_debuglevel(1)  # Show detailed communication
        
        if tls:
            print("Starting TLS...")
            server.starttls()
        
        print("Logging in...")
        server.login(user, password)
        
        print("✅ Login successful!")
        
        # Optional: Send a real test email
        # msg = MIMEText("This is a test email from the Anveshan debugger script.")
        # msg['Subject'] = "Anveshan SMTP Test"
        # msg['From'] = user
        # msg['To'] = user
        # server.send_message(msg)
        # print("✅ Test email sent to yourself!")

        server.quit()
        print("\nSUCCESS: Your SMTP configuration is correct.")
        
    except Exception as e:
        print(f"\n❌ FAILED: {str(e)}")
        print("\nTroubleshooting tips:")
        print("1. If using Gmail, you MUST use an 'App Password', not your login password.")
        print("2. Check if 2-Step Verification is enabled on your Google Account.")
        print("3. Ensure your firewall/antivirus isn't blocking port 587.")

if __name__ == "__main__":
    test_smtp()