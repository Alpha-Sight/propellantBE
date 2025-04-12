class RulesService:
    @staticmethod
    def get_rules() -> dict:
        """
        Returns a dictionary of rules for CV generation.
        """
        return {
            "rule1": "Use active language.",
            "rule2": "Tailor skills to job description.",
            "rule3": "Highlight quantifiable achievements.",
            # Add more rules as needed
        }