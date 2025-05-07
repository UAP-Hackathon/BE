import json
from typing import List, Dict, Any, Optional
import openai
from config import settings

# Set OpenAI API key
openai.api_key = settings.apikey

class SkillAssessment:
    @staticmethod
    def generate_questions(skills: List[str], num_questions: int = 5, question_type: str = "mixed") -> List[Dict[str, Any]]:
        """
        Generate skill assessment questions based on the provided skills
        
        Args:
            skills: List of skills to generate questions for
            num_questions: Number of questions to generate
            question_type: Type of questions to generate (mcq, short_answer, or mixed)
            
        Returns:
            List of question objects
        """
        if not skills:
            return []
            
        # Format skills for the prompt
        skills_text = ", ".join(skills)
        
        # Determine question type distribution
        mcq_count = 0
        short_answer_count = 0
        
        if question_type == "mcq":
            mcq_count = num_questions
        elif question_type == "short_answer":
            short_answer_count = num_questions
        else:  # mixed
            mcq_count = num_questions // 2
            short_answer_count = num_questions - mcq_count
            
        # Create the prompt for OpenAI
        prompt = f"""
        Generate a skill assessment with {num_questions} questions for a job candidate with the following skills: {skills_text}.
        
        Include {mcq_count} multiple-choice questions and {short_answer_count} short answer questions.
        
        For multiple-choice questions, provide 4 options with one correct answer.
        
        Format the response as a JSON array with the following structure:
        [
            {{
                "question": "Question text",
                "type": "mcq",
                "options": ["Option A", "Option B", "Option C", "Option D"],
                "correct_answer": "The correct option",
                "explanation": "Explanation of the correct answer"
            }},
            {{
                "question": "Short answer question text",
                "type": "short_answer",
                "sample_answer": "A sample correct answer",
                "key_points": ["Key point 1", "Key point 2", "Key point 3"]
            }}
        ]
        
        Make sure the questions are challenging but appropriate for a technical interview.
        """
        
        try:
            # Call OpenAI API
            response = openai.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a technical interviewer creating skill assessment questions."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=2000
            )
            
            # Extract and parse the response
            content = response.choices[0].message.content
            
            # Find JSON content (it might be wrapped in markdown code blocks)
            json_content = content
            if "```json" in content:
                json_content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                json_content = content.split("```")[1].split("```")[0].strip()
                
            # Parse JSON
            questions = json.loads(json_content)
            return questions
            
        except Exception as e:
            print(f"Error generating questions: {e}")
            return []
    
    @staticmethod
    def evaluate_answer(question: Dict[str, Any], user_answer: str) -> Dict[str, Any]:
        """
        Evaluate a user's answer to a question
        
        Args:
            question: Question object
            user_answer: User's answer to the question
            
        Returns:
            Evaluation result
        """
        try:
            if question["type"] == "mcq":
                # For MCQs, check if the answer matches exactly
                is_correct = user_answer.strip() == question["correct_answer"].strip()
                
                return {
                    "is_correct": is_correct,
                    "correct_answer": question["correct_answer"],
                    "explanation": question["explanation"] if "explanation" in question else None
                }
            else:  # short_answer
                # For short answers, use OpenAI to evaluate
                prompt = f"""
                Question: {question["question"]}
                
                Sample correct answer: {question["sample_answer"]}
                
                Key points that should be addressed:
                {", ".join(question["key_points"])}
                
                User's answer: {user_answer}
                
                Evaluate the user's answer. Consider:
                1. Does it address the key points?
                2. Is it technically accurate?
                3. How complete is the answer?
                
                Return a JSON object with the following format:
                {{
                    "score": [A score from 0-10],
                    "feedback": "Detailed feedback on the answer",
                    "missing_points": ["Any key points that were missed"],
                    "is_correct": [true if score >= 7, false otherwise]
                }}
                """
                
                response = openai.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[
                        {"role": "system", "content": "You are a technical interviewer evaluating candidate responses."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.3,
                    max_tokens=1000
                )
                
                # Extract and parse the response
                content = response.choices[0].message.content
                
                # Find JSON content
                json_content = content
                if "```json" in content:
                    json_content = content.split("```json")[1].split("```")[0].strip()
                elif "```" in content:
                    json_content = content.split("```")[1].split("```")[0].strip()
                    
                # Parse JSON
                evaluation = json.loads(json_content)
                return evaluation
                
        except Exception as e:
            print(f"Error evaluating answer: {e}")
            return {
                "is_correct": False,
                "error": str(e),
                "score": 0,
                "feedback": "There was an error evaluating your answer."
            }
