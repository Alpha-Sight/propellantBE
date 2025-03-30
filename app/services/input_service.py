from app.models.requests import CVAnalysisRequest

class InputService:
    @staticmethod
    def validate_input(data: CVAnalysisRequest) -> CVAnalysisRequest:
        # Perform any additional validation or preprocessing here
        return data