import requests
from bs4 import BeautifulSoup
import os
import time

# Define the category mapping and target URLs
DOCS_STRUCTURE = {
    "admin": [
        "https://help.anthology.com/blackboard/administrator/en/getting-started.html",
        "https://help.anthology.com/blackboard/administrator/en/user-management.html",
        "https://help.anthology.com/blackboard/administrator/en/authentication.html",
        "https://help.anthology.com/blackboard/administrator/en/courses-and-organizations.html",
        "https://help.anthology.com/blackboard/administrator/en/system-management.html",
        "https://help.anthology.com/blackboard/administrator/en/tools-management.html"
    ],
    "instructor": [
        "https://help.anthology.com/blackboard/instructor/en/getting-started.html",
        "https://help.anthology.com/blackboard/instructor/en/blackboard-app.html",
        "https://help.anthology.com/blackboard/instructor/en/course-and-content-management.html",
        "https://help.anthology.com/blackboard/instructor/en/interact-with-students.html",
        "https://help.anthology.com/blackboard/instructor/en/assessments.html",
        "https://help.anthology.com/blackboard/instructor/en/grading.html",
        "https://help.anthology.com/blackboard/instructor/en/plagiarism-tools.html"
    ],
    "student": [
        "https://help.anthology.com/blackboard/student/en/getting-started.html",
        "https://help.anthology.com/blackboard/student/en/course-content-and-materials.html",
        "https://help.anthology.com/blackboard/student/en/interact-with-others.html",
        "https://help.anthology.com/blackboard/student/en/assessments.html",
        "https://help.anthology.com/blackboard/student/en/grades.html",
        "https://help.anthology.com/blackboard/student/en/plagiarism.html",
        "https://help.anthology.com/blackboard/student/en/original-course-view.html"
    ]
}

BASE_DIR = "blackboard_docs"

def setup_directories():
    for role in DOCS_STRUCTURE.keys():
        os.makedirs(os.path.join(BASE_DIR, role), exist_ok=True)

def scrape_categorized_urls():
    for role, urls in DOCS_STRUCTURE.items():
        print(f"\n--- Scraping {role.upper()} Documentation ---")
        
        for url in urls:
            try:
                time.sleep(1) # Prevent rate-limiting
                response = requests.get(url, timeout=10)
                response.raise_for_status()
                
                soup = BeautifulSoup(response.text, 'html.parser')
                main_content = soup.find('main') or soup.find('article')
                
                if main_content:
                    text = main_content.get_text(separator='\n', strip=True)
                    filename = url.split('/')[-1].replace('.html', '.txt')
                    filepath = os.path.join(BASE_DIR, role, filename)
                    
                    with open(filepath, 'w', encoding='utf-8') as f:
                        f.write(text)
                    print(f"Saved: {filepath}")
                else:
                    print(f"Skipped (No main content): {url}")
                    
            except Exception as e:
                print(f"Failed on {url}: {e}")

if __name__ == "__main__":
    setup_directories()
    scrape_categorized_urls()
    print("\nData collection complete. Ready for ChromaDB chunking.")