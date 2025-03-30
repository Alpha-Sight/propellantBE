from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_cv_analysis():
    response = client.post("/api/cv-analysis", json={
        "job_title": "Software Engineer",
        "experience_years": "5",
        "skills": "Python, JavaScript",
        "current_role": "Developer",
        "job_description": "Develop software applications",
        "cv_text": "Experienced developer with a background in software engineering.",
        "cv_template": "Template1"
    })
    assert response.status_code == 200
    assert "skills" in response.json()
    assert "work_experience" in response.json()

def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}