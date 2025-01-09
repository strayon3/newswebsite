from flask import Flask, render_template,request,redirect,url_for,flash
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from dotenv import load_dotenv
import os
import json
from datetime import datetime, timedelta
import requests
from keys import news_api

# Initialize the app
app = Flask(__name__, template_folder='.', static_folder='./static')

#loads in env file
load_dotenv()
EMAIL_USER = os.getenv("email_a")
EMAIL_PASS = os.getenv("email_p")
EMAIL_SENDER = os.getenv("sender")

#files for saved data
LAST_UPDATE_FILE = "last_update.txt"
ARTICLES_DATA_FILE = "articles_data.json"
#api information
API_KEY = news_api
NEWS_API_URL = "https://newsapi.org/v2/top-headlines"

# Function to check if 1 day has passed
def daily_check(last_run_date, today):
    last_run = datetime.strptime(last_run_date, "%Y-%m-%d")
    difference = today - last_run
    return difference >= timedelta(days=1)

# Function to save article data (overwrites existing file)
def save_article_data(articles):
    with open(ARTICLES_DATA_FILE, "w", encoding="utf-8") as file:
        json.dump(articles, file, ensure_ascii=False, indent=4)

# Function to load saved article data
def load_article_data():
    articles = []
    if os.path.exists(ARTICLES_DATA_FILE):
        with open(ARTICLES_DATA_FILE, "r", encoding="utf-8") as file:
            articles = json.load(file)
    return articles

# Function to check and update articles daily
def check_and_update():
    today = datetime.now()
    last_update_date = None

    # Load last update date from the file if it exists
    if os.path.exists(LAST_UPDATE_FILE):
        with open(LAST_UPDATE_FILE, 'r') as file:
            last_update_date = file.read().strip()

    # Check if 1 day has passed or it's the first run
    if last_update_date is None or daily_check(last_update_date, today):
        trending_articles = get_trending_articles(category="general", limit=16)
        tech_articles = get_trending_articles(category="technology", limit=16)

        # Combine both lists of articles
        all_articles = trending_articles + tech_articles

        # Filter articles: remove those with "removed" title or missing data
        valid_articles = [article for article in all_articles if article.get("title") != "removed" and article.get("title")]

        # Save the new date
        with open(LAST_UPDATE_FILE, "w") as file:
            file.write(today.strftime("%Y-%m-%d"))

        # Save the fetched article data, replacing any existing data
        save_article_data(valid_articles)

        # Check if the total number of articles is enough (32), and if not, request additional articles
        missing_count = 32 - len(valid_articles)
        if missing_count > 0:
            print(f"Missing {missing_count} articles, requesting more...")
            more_articles = get_trending_articles(category="science", limit=missing_count)
            valid_articles += more_articles

        return valid_articles, True  # Return articles and a flag indicating they were updated
    else:
        # Load the saved articles
        articles = load_article_data()
        return articles, False  # No update, return saved articles

# Function to fetch trending articles from the API
def get_trending_articles(category, limit=10):
    url = f"{NEWS_API_URL}?category={category}&apiKey={API_KEY}&pageSize={limit}"
    response = requests.get(url)
    data = response.json()

    valid_articles = []
    for article in data["articles"]:
        if article.get("url") and article.get("title") and article.get("title") != "removed":
            valid_articles.append({
                "title": article["title"],
                "url": article["url"],
                "thumbnail": article.get("urlToImage", ""),
                "publishedAt": article["publishedAt"]
            })

    return valid_articles

# Function to send email (using smtplib)
# Function to send email
def send_email(name, email, message):
    try:
        # Set up the SMTP server
        server = smtplib.SMTP('smtp.gmail.com', 587)  # Using Gmail SMTP server
        server.starttls()  # Start TLS encryption

        # Login to your email account
        server.login(EMAIL_USER, EMAIL_PASS)

        # Compose the email
        msg = MIMEMultipart()
        msg['From'] = EMAIL_USER
        msg['To'] = EMAIL_SENDER  # Get recipient from the environment
        msg['Subject'] = f"New Contact Form Submission from {name}"

        # Create the body of the email
        body = f"Name: {name}\nEmail: {email}\nMessage: {message}"
        msg.attach(MIMEText(body, 'plain'))

        # Send the email
        server.sendmail(EMAIL_USER, EMAIL_SENDER, msg.as_string())

        # Close the connection
        server.quit()

        return True
    except Exception as e:
        print(f"Error sending email: {e}")
        return False

# Route for the homepage
@app.route('/')
def home():
    articles, updated = check_and_update()
    if updated:
        print("Articles updated.")
    else:
        print("No update needed. Using cached articles.")
    return render_template("template/index.html", articles=articles)

# Route for About page
@app.route('/about')
def about():
    return render_template("/template/about.html")

# Route for Contact page
@app.route('/contact', methods=['GET', 'POST'])
def contact():
    if request.method == 'POST':
        # Collect form data
        name = request.form.get('name')
        email = request.form.get('email')
        message = request.form.get('message')

        # Basic validation (you can improve it as needed)
        if not name or not email or not message:
            flash("Please fill in all fields.", "error")
            return redirect(url_for('contact'))

        # Send the email with form data
        email_sent = send_email(name, email, message)
        if email_sent:
            flash("Your message has been submitted successfully!", "success")
        else:
            flash("There was an error sending your message. Please try again later.", "error")

        return redirect(url_for('contact'))

    return render_template("/template/contact.html")




if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0",port=port,debug=True)
