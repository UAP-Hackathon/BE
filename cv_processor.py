import PyPDF2
import io
import re

# Try to use NLTK if available, but provide fallbacks
try:
    import nltk
    from nltk.corpus import stopwords
    from nltk.tokenize import word_tokenize, sent_tokenize
    NLTK_AVAILABLE = True
except ImportError:
    NLTK_AVAILABLE = False

class CVProcessor:
    @staticmethod
    def extract_text_from_pdf(pdf_data):
        """Extract text from PDF binary data"""
        try:
            # Create a PDF reader object
            pdf_reader = PyPDF2.PdfReader(io.BytesIO(pdf_data))
            
            # Extract text from all pages
            text = ""
            for page_num in range(len(pdf_reader.pages)):
                page = pdf_reader.pages[page_num]
                text += page.extract_text()
                
            return text
        except Exception as e:
            print(f"Error extracting text from PDF: {e}")
            return None
    
    @staticmethod
    def generate_summary(text, num_sentences=5):
        """Generate a summary of the given text"""
        if not text:
            return "Could not extract text from the PDF."
        
        try:
            # Simple sentence splitting as fallback if NLTK is not available
            if NLTK_AVAILABLE:
                try:
                    sentences = sent_tokenize(text)
                except Exception:
                    # Fallback to simple sentence splitting
                    sentences = [s.strip() for s in re.split(r'[.!?]+', text) if s.strip()]
            else:
                sentences = [s.strip() for s in re.split(r'[.!?]+', text) if s.strip()]
            
            # If there are fewer sentences than requested, return all sentences
            if len(sentences) <= num_sentences:
                return " ".join(sentences)
            
            # Simple word tokenization and stopword filtering
            if NLTK_AVAILABLE:
                try:
                    stop_words = set(stopwords.words('english'))
                    word_tokens = word_tokenize(text.lower())
                    filtered_words = [word for word in word_tokens if word.isalnum() and word not in stop_words]
                except Exception:
                    # Fallback to simple word splitting
                    common_stopwords = {'a', 'an', 'the', 'and', 'or', 'but', 'is', 'are', 'was', 'were', 'be', 'been', 'being', 'in', 'on', 'at', 'to', 'for', 'with', 'by', 'about', 'of'}
                    word_tokens = re.findall(r'\b\w+\b', text.lower())
                    filtered_words = [word for word in word_tokens if word.isalnum() and word not in common_stopwords]
            else:
                common_stopwords = {'a', 'an', 'the', 'and', 'or', 'but', 'is', 'are', 'was', 'were', 'be', 'been', 'being', 'in', 'on', 'at', 'to', 'for', 'with', 'by', 'about', 'of'}
                word_tokens = re.findall(r'\b\w+\b', text.lower())
                filtered_words = [word for word in word_tokens if word.isalnum() and word not in common_stopwords]
            
            # Calculate word frequencies
            word_freq = {}
            for word in filtered_words:
                if word in word_freq:
                    word_freq[word] += 1
                else:
                    word_freq[word] = 1
            
            # Calculate sentence scores based on word frequencies
            sentence_scores = {}
            for i, sentence in enumerate(sentences):
                if NLTK_AVAILABLE:
                    try:
                        sentence_words = word_tokenize(sentence.lower())
                    except Exception:
                        sentence_words = re.findall(r'\b\w+\b', sentence.lower())
                else:
                    sentence_words = re.findall(r'\b\w+\b', sentence.lower())
                    
                score = 0
                for word in sentence_words:
                    if word in word_freq:
                        score += word_freq[word]
                sentence_scores[i] = score
            
            # Get the top N sentences with highest scores
            top_sentences_indices = sorted(sentence_scores, key=sentence_scores.get, reverse=True)[:num_sentences]
            top_sentences_indices.sort()  # Sort by original order
            
            # Combine the top sentences to form the summary
            summary = " ".join([sentences[i] for i in top_sentences_indices])
            
            return summary
        except Exception as e:
            print(f"Error generating summary: {e}")
            return "Error generating summary."
    
    @staticmethod
    def extract_key_info(text):
        """Extract key information from the CV text"""
        if not text:
            return {}
        
        # Initialize result dictionary
        info = {
            "name": None,
            "email": None,
            "phone": None,
            "skills": [],
            "education": [],
            "experience": []
        }
        
        # Simple extraction based on common patterns
        lines = text.split('\n')
        
        # Process each line
        for i, line in enumerate(lines):
            line = line.strip()
            
            # Skip empty lines
            if not line:
                continue
                
            # Look for email using simple pattern
            if '@' in line and '.' in line and not info['email']:
                words = line.split()
                for word in words:
                    if '@' in word and '.' in word:
                        info['email'] = word
                        break
            
            # Look for phone numbers (simple pattern)
            if any(c.isdigit() for c in line) and not info['phone']:
                # Check if line has a phone number pattern
                digits = ''.join(c for c in line if c.isdigit())
                if len(digits) >= 10:
                    info['phone'] = line
            
            # Look for skills section
            if 'SKILLS' in line.upper() or 'TECHNICAL SKILLS' in line.upper():
                # Extract skills from the next few lines
                j = i + 1
                while j < len(lines) and j < i + 10:
                    if lines[j].strip() and not any(header in lines[j].upper() for header in ['EDUCATION', 'EXPERIENCE', 'WORK']):
                        # Split by commas or other separators
                        skills = [s.strip() for s in lines[j].split(',')]
                        info['skills'].extend([s for s in skills if s])
                    j += 1
            
            # Look for education
            if 'EDUCATION' in line.upper():
                j = i + 1
                current_edu = ""
                while j < len(lines) and j < i + 15:
                    if lines[j].strip() and not any(header in lines[j].upper() for header in ['SKILLS', 'EXPERIENCE', 'WORK']):
                        current_edu += lines[j].strip() + " "
                    else:
                        if current_edu:
                            info['education'].append(current_edu.strip())
                            current_edu = ""
                    j += 1
                if current_edu:
                    info['education'].append(current_edu.strip())
            
            # Look for experience
            if 'EXPERIENCE' in line.upper() or 'WORK EXPERIENCE' in line.upper():
                j = i + 1
                current_exp = ""
                while j < len(lines) and j < i + 20:
                    if lines[j].strip() and not any(header in lines[j].upper() for header in ['SKILLS', 'EDUCATION']):
                        current_exp += lines[j].strip() + " "
                    else:
                        if current_exp:
                            info['experience'].append(current_exp.strip())
                            current_exp = ""
                    j += 1
                if current_exp:
                    info['experience'].append(current_exp.strip())
        
        # Try to extract name from the beginning of the document
        if lines and lines[0].strip():
            info['name'] = lines[0].strip()
        
        return info
