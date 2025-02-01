from flask import Flask, request, jsonify
from flask_cors import CORS
from bs4 import BeautifulSoup
import requests
import re
import logging

app = Flask(__name__)
CORS(app)  # Enable CORS for cross-origin requests

class QAScraper:
    def fetch_page(self, url):
        try:
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            response.encoding = 'utf-8'
            return response.text
        except requests.RequestException as e:
            raise Exception(f"Error fetching URL: {e}")

    def extract_qa(self, html):
        soup = BeautifulSoup(html, 'html.parser')
        qa_pairs = []
        content_div = soup.find('div', class_='td-post-content tagdiv-type')
        
        if not content_div:
            return qa_pairs

        ol_tags = content_div.find_all("ol")
        
        for ol in ol_tags:
            li = ol.find("li")
            if not li:
                continue

            question = li.get_text(separator=" ", strip=True)
            answer = ""
            
            if "Ans:" in question:
                parts = question.split("Ans:", 1)
                question = parts[0].strip()
                answer = parts[1].strip()
            else:
                options = []
                sibling = ol.find_next_sibling()
                while sibling and sibling.name == "p":
                    text = sibling.get_text(separator=" ", strip=True)
                    if text.startswith("Ans:"):
                        answer_text = text.split("Ans:", 1)[1].strip()
                        answer = "Options:\n" + "\n".join(options) + "\nAnswer: " + answer_text if options else answer_text
                        break
                    else:
                        options.append(text)
                    sibling = sibling.find_next_sibling()
                
                if not answer and options:
                    answer = "Options:\n" + "\n".join(options)
            
            if question and answer:
                qa_pairs.append({"question": question, "answer": answer})
        
        return qa_pairs

def extract_topic_title(html):
    soup = BeautifulSoup(html, 'html.parser')
    full_title = soup.title.get_text(strip=True)
    topic_part = full_title.split("প্রশ্ন ও উত্তর")[0].strip()
    prefix = "উচ্চমাধ্যমিক "
    return topic_part[len(prefix):] if topic_part.startswith(prefix) else topic_part

@app.route('/scrape', methods=['POST'])
def scrape():
    data = request.get_json()
    if not data or 'url' not in data:
        return jsonify({"error": "URL is required"}), 400
    
    scraper = QAScraper()
    try:
        html = scraper.fetch_page(data['url'])
        topic_title = extract_topic_title(html)
        qa_pairs = scraper.extract_qa(html)
        
        if not qa_pairs:
            return jsonify({"error": "No Q&A pairs found"}), 404
            
        return jsonify({
            "topic": topic_title,
            "qa_pairs": qa_pairs
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500




# Add this new route to api.py
@app.route('/generate_txt', methods=['POST'])
def generate_txt():
    data = request.get_json()
    if not data or 'qa_pairs' not in data or 'topic' not in data:
        return jsonify({"error": "Missing required data"}), 400
    
    try:
        text_content = "Questions and Answers\n"
        text_content += "===================\n\n"
        text_content += f"{data['topic']}\n\n"
        
        for i, pair in enumerate(data['qa_pairs'], 1):
            text_content += f"{i}. {pair['question']}\n\n"
            if "Options:" not in pair['answer']:
                text_content += f"ANS:- {pair['answer']}\n\n"
            else:
                text_content += f"{pair['answer']}\n\n"
            text_content += "-" * 80 + "\n\n"
        
        return jsonify({
            "content": text_content,
            "filename": f"{data['topic']}.txt".replace(" ", "_")
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)