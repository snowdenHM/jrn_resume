from typing import Dict, List, Any
import logging
import re
from textstat import flesch_reading_ease, flesch_kincaid_grade

from app.schemas.cover_letter import CoverLetterValidation

logger = logging.getLogger(__name__)


class CoverLetterValidationService:
    """Service for validating cover letter content and providing recommendations"""

    def __init__(self):
        self.optimal_word_range = {"min": 250, "max": 400}
        self.max_paragraph_length = 150  # words per paragraph
        self.common_weak_phrases = [
            "to whom it may concern",
            "i am writing to apply",
            "please consider my application",
            "i would like to apply",
            "dear sir or madam",
            "i hope this letter finds you well"
        ]
        self.power_words = [
            "achieved", "accomplished", "advanced", "built", "created", "delivered",
            "developed", "enhanced", "exceeded", "expanded", "generated", "improved",
            "increased", "influenced", "initiated", "launched", "led", "managed",
            "optimized", "pioneered", "produced", "streamlined", "strengthened"
        ]

    def validate_cover_letter_content(self, content: Dict[str, Any]) -> CoverLetterValidation:
        """Validate complete cover letter content and return validation results"""
        try:
            validation_errors = []
            recommendations = []

            # Extract content sections
            opening = content.get('opening_paragraph', '')
            body_paragraphs = content.get('body_paragraphs', [])
            closing = content.get('closing_paragraph', '')

            # Validate structure
            structure_errors = self._validate_structure(opening, body_paragraphs, closing)
            validation_errors.extend(structure_errors)

            # Calculate word count
            word_count = self._calculate_word_count(opening, body_paragraphs, closing)

            # Validate word count
            word_count_errors = self._validate_word_count(word_count)
            validation_errors.extend(word_count_errors)

            # Calculate completeness
            completeness_percentage = self._calculate_completeness(opening, body_paragraphs, closing)

            # Generate content recommendations
            content_recommendations = self._generate_content_recommendations(
                opening, body_paragraphs, closing, word_count
            )
            recommendations.extend(content_recommendations)

            # Generate style recommendations
            style_recommendations = self._generate_style_recommendations(
                opening, body_paragraphs, closing
            )
            recommendations.extend(style_recommendations)

            # Calculate overall score
            score = self._calculate_overall_score(
                completeness_percentage, word_count, validation_errors, content
            )

            return CoverLetterValidation(
                is_valid=len(validation_errors) == 0,
                completeness_percentage=completeness_percentage,
                validation_errors=validation_errors,
                recommendations=recommendations,
                word_count=word_count,
                optimal_word_range=self.optimal_word_range,
                score=score
            )

        except Exception as e:
            logger.error(f"Error validating cover letter content: {e}")
            raise

    def _validate_structure(self, opening: str, body_paragraphs: List[str], closing: str) -> List[str]:
        """Validate cover letter structure"""
        errors = []

        # Check opening paragraph
        if not opening or not opening.strip():
            errors.append("Opening paragraph is required")
        elif len(opening.strip()) < 20:
            errors.append("Opening paragraph is too short (minimum 20 characters)")

        # Check body paragraphs
        if not body_paragraphs:
            errors.append("At least one body paragraph is required")
        else:
            for i, paragraph in enumerate(body_paragraphs):
                if not paragraph or not paragraph.strip():
                    errors.append(f"Body paragraph {i + 1} cannot be empty")
                elif len(paragraph.strip()) < 30:
                    errors.append(f"Body paragraph {i + 1} is too short (minimum 30 characters)")

        # Check closing paragraph
        if not closing or not closing.strip():
            errors.append("Closing paragraph is required")
        elif len(closing.strip()) < 20:
            errors.append("Closing paragraph is too short (minimum 20 characters)")

        return errors

    def _validate_word_count(self, word_count: int) -> List[str]:
        """Validate word count against optimal range"""
        errors = []

        if word_count < 100:
            errors.append("Cover letter is too short (minimum 100 words)")
        elif word_count > 600:
            errors.append("Cover letter is too long (maximum 600 words)")

        return errors

    def _calculate_word_count(self, opening: str, body_paragraphs: List[str], closing: str) -> int:
        """Calculate total word count"""
        total_words = 0

        if opening:
            total_words += len(opening.split())

        for paragraph in body_paragraphs:
            if paragraph:
                total_words += len(paragraph.split())

        if closing:
            total_words += len(closing.split())

        return total_words

    def _calculate_completeness(self, opening: str, body_paragraphs: List[str], closing: str) -> int:
        """Calculate completeness percentage"""
        sections = {
            'opening': bool(opening and opening.strip()),
            'body': bool(body_paragraphs and any(p.strip() for p in body_paragraphs)),
            'closing': bool(closing and closing.strip()),
            'sufficient_length': self._calculate_word_count(opening, body_paragraphs, closing) >= 200
        }

        completed_sections = sum(1 for completed in sections.values() if completed)
        total_sections = len(sections)

        return int((completed_sections / total_sections) * 100)

    def _generate_content_recommendations(
            self,
            opening: str,
            body_paragraphs: List[str],
            closing: str,
            word_count: int
    ) -> List[str]:
        """Generate content-specific recommendations"""
        recommendations = []

        # Word count recommendations
        if word_count < self.optimal_word_range["min"]:
            recommendations.append(
                f"Consider expanding your cover letter. Aim for {self.optimal_word_range['min']}-{self.optimal_word_range['max']} words."
            )
        elif word_count > self.optimal_word_range["max"]:
            recommendations.append(
                f"Consider condensing your cover letter. Aim for {self.optimal_word_range['min']}-{self.optimal_word_range['max']} words."
            )

        # Opening paragraph recommendations
        if opening:
            opening_lower = opening.lower()
            for weak_phrase in self.common_weak_phrases:
                if weak_phrase in opening_lower:
                    recommendations.append(
                        f"Consider replacing '{weak_phrase}' with a more engaging opening"
                    )
                    break

            if not self._contains_company_or_position(opening):
                recommendations.append(
                    "Mention the specific position and company in your opening paragraph"
                )

        # Body paragraph recommendations
        if body_paragraphs:
            has_specific_examples = any(
                self._contains_specific_examples(paragraph) for paragraph in body_paragraphs
            )
            if not has_specific_examples:
                recommendations.append(
                    "Include specific examples of your achievements and experiences"
                )

            has_quantifiable_results = any(
                self._contains_numbers(paragraph) for paragraph in body_paragraphs
            )
            if not has_quantifiable_results:
                recommendations.append(
                    "Add quantifiable results (numbers, percentages, metrics) to strengthen your claims"
                )

        # Closing paragraph recommendations
        if closing and not self._contains_call_to_action(closing):
            recommendations.append(
                "Include a clear call to action in your closing paragraph"
            )

        return recommendations

    def _generate_style_recommendations(
            self,
            opening: str,
            body_paragraphs: List[str],
            closing: str
    ) -> List[str]:
        """Generate style and tone recommendations"""
        recommendations = []

        all_text = ' '.join([opening] + body_paragraphs + [closing])

        # Check for power words
        power_word_count = sum(
            1 for word in self.power_words
            if word.lower() in all_text.lower()
        )

        if power_word_count < 3:
            recommendations.append(
                "Use more action verbs and power words to make your achievements stand out"
            )

        # Check for passive voice
        passive_voice_patterns = [
            r'\bwas\s+\w+ed\b',
            r'\bwere\s+\w+ed\b',
            r'\bis\s+\w+ed\b',
            r'\bare\s+\w+ed\b',
            r'\bbeen\s+\w+ed\b'
        ]

        passive_voice_count = sum(
            len(re.findall(pattern, all_text, re.IGNORECASE))
            for pattern in passive_voice_patterns
        )

        if passive_voice_count > 2:
            recommendations.append(
                "Reduce passive voice usage. Use active voice to sound more confident and direct"
            )

        # Check paragraph length
        long_paragraphs = []
        for i, paragraph in enumerate(body_paragraphs):
            if paragraph and len(paragraph.split()) > self.max_paragraph_length:
                long_paragraphs.append(i + 1)

        if long_paragraphs:
            recommendations.append(
                f"Consider breaking up long paragraphs (paragraph {', '.join(map(str, long_paragraphs))})"
            )

        # Check for repetitive language
        words = all_text.lower().split()
        word_frequency = {}
        for word in words:
            if len(word) > 4 and word.isalpha():  # Only count meaningful words
                word_frequency[word] = word_frequency.get(word, 0) + 1

        repetitive_words = [word for word, count in word_frequency.items() if count > 3]
        if repetitive_words:
            recommendations.append(
                "Vary your vocabulary to avoid repetition of words like: " + ", ".join(repetitive_words[:3])
            )

        # Reading level check
        try:
            reading_ease = flesch_reading_ease(all_text)
            if reading_ease < 30:  # Very difficult
                recommendations.append(
                    "Simplify your language for better readability"
                )
            elif reading_ease > 90:  # Very easy
                recommendations.append(
                    "Consider using more sophisticated vocabulary to match professional standards"
                )
        except:
            # Skip reading level analysis if textstat fails
            pass

        return recommendations

    def _calculate_overall_score(
            self,
            completeness_percentage: int,
            word_count: int,
            validation_errors: List[str],
            content: Dict[str, Any]
    ) -> int:
        """Calculate overall cover letter score (0-100)"""
        score = completeness_percentage * 0.4  # 40% weight for completeness

        # Word count score (20% weight)
        word_score = 0
        if self.optimal_word_range["min"] <= word_count <= self.optimal_word_range["max"]:
            word_score = 20
        elif word_count < self.optimal_word_range["min"]:
            word_score = max(0, 20 - (self.optimal_word_range["min"] - word_count) * 0.1)
        else:  # word_count > optimal_max
            word_score = max(0, 20 - (word_count - self.optimal_word_range["max"]) * 0.05)

        score += word_score

        # Quality factors (40% weight)
        quality_score = 0

        # Check for specific examples and achievements
        all_text = ' '.join([
            content.get('opening_paragraph', ''),
            ' '.join(content.get('body_paragraphs', [])),
            content.get('closing_paragraph', '')
        ])

        if self._contains_specific_examples(all_text):
            quality_score += 10

        if self._contains_numbers(all_text):
            quality_score += 10

        if not any(weak in all_text.lower() for weak in self.common_weak_phrases):
            quality_score += 5

        power_word_count = sum(
            1 for word in self.power_words
            if word.lower() in all_text.lower()
        )
        quality_score += min(10, power_word_count * 2)

        if self._contains_company_or_position(all_text):
            quality_score += 5

        score += quality_score

        # Penalty for validation errors
        error_penalty = len(validation_errors) * 5
        score = max(0, score - error_penalty)

        return int(min(100, score))

    def _contains_company_or_position(self, text: str) -> bool:
        """Check if text contains specific company or position references"""
        # Look for patterns that suggest specific company/position mentions
        patterns = [
            r'\b(?:at|with|for)\s+[A-Z][a-zA-Z\s&]+(?:Inc|LLC|Corp|Company|Technologies|Solutions)\b',
            r'\b(?:position|role|job)\s+(?:of|as)\s+[A-Z][a-zA-Z\s]+\b',
            r'\b[A-Z][a-zA-Z\s]+(?:Engineer|Manager|Developer|Analyst|Specialist|Coordinator)\b'
        ]

        return any(re.search(pattern, text) for pattern in patterns)

    def _contains_specific_examples(self, text: str) -> bool:
        """Check if text contains specific examples or achievements"""
        example_indicators = [
            'for example', 'for instance', 'specifically', 'in particular',
            'during my time', 'while working', 'in my role', 'as a result',
            'led to', 'resulted in', 'achieved', 'accomplished', 'implemented',
            'developed', 'created', 'managed', 'improved', 'increased'
        ]

        text_lower = text.lower()
        return any(indicator in text_lower for indicator in example_indicators)

    def _contains_numbers(self, text: str) -> bool:
        """Check if text contains numbers/metrics"""
        number_patterns = [
            r'\d+%',  # percentages
            r'\$\d+',  # dollar amounts
            r'\d+\s*(?:million|thousand|billion)',  # large numbers
            r'\d+\s*(?:years?|months?|weeks?)',  # time periods
            r'\d+\s*(?:people|employees|clients|customers)',  # quantities
            r'\b\d+\b'  # any number
        ]

        return any(re.search(pattern, text, re.IGNORECASE) for pattern in number_patterns)

    def _contains_call_to_action(self, text: str) -> bool:
        """Check if closing contains a call to action"""
        call_to_action_phrases = [
            'look forward to hearing',
            'would welcome the opportunity',
            'would love to discuss',
            'eager to discuss',
            'excited to learn more',
            'hope to hear from you',
            'thank you for your consideration',
            'please contact me',
            'would be happy to provide',
            'available for an interview'
        ]

        text_lower = text.lower()
        return any(phrase in text_lower for phrase in call_to_action_phrases)

    def analyze_tone_and_style(self, content: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze tone and style of cover letter"""
        try:
            all_text = ' '.join([
                content.get('opening_paragraph', ''),
                ' '.join(content.get('body_paragraphs', [])),
                content.get('closing_paragraph', '')
            ])

            analysis = {
                'tone': self._analyze_tone(all_text),
                'formality_level': self._analyze_formality(all_text),
                'confidence_level': self._analyze_confidence(all_text),
                'enthusiasm_level': self._analyze_enthusiasm(all_text),
                'word_variety': self._analyze_word_variety(all_text),
                'sentence_complexity': self._analyze_sentence_complexity(all_text)
            }

            return analysis

        except Exception as e:
            logger.error(f"Error analyzing tone and style: {e}")
            return {}

    def _analyze_tone(self, text: str) -> str:
        """Analyze overall tone of the text"""
        positive_words = [
            'excited', 'enthusiastic', 'passionate', 'thrilled', 'delighted',
            'confident', 'optimistic', 'motivated', 'inspired', 'eager'
        ]

        formal_words = [
            'respectfully', 'accordingly', 'furthermore', 'subsequently',
            'consequently', 'therefore', 'nonetheless', 'nevertheless'
        ]

        casual_words = [
            'really', 'pretty', 'quite', 'totally', 'absolutely',
            'definitely', 'honestly', 'basically', 'obviously'
        ]

        text_lower = text.lower()

        positive_count = sum(1 for word in positive_words if word in text_lower)
        formal_count = sum(1 for word in formal_words if word in text_lower)
        casual_count = sum(1 for word in casual_words if word in text_lower)

        if positive_count > 2:
            if formal_count > casual_count:
                return "Professional and Enthusiastic"
            else:
                return "Enthusiastic"
        elif formal_count > casual_count:
            return "Professional"
        elif casual_count > 0:
            return "Too Casual"
        else:
            return "Neutral"

    def _analyze_formality(self, text: str) -> str:
        """Analyze formality level"""
        contractions = ["don't", "can't", "won't", "I'm", "I've", "I'd", "I'll"]
        formal_transitions = ["furthermore", "moreover", "consequently", "therefore"]

        contraction_count = sum(1 for contraction in contractions if contraction in text)
        formal_transition_count = sum(1 for transition in formal_transitions if transition in text)

        if contraction_count > 2:
            return "Too Informal"
        elif formal_transition_count > 1:
            return "Very Formal"
        else:
            return "Appropriately Formal"

    def _analyze_confidence(self, text: str) -> str:
        """Analyze confidence level in the text"""
        confident_phrases = [
            "I am confident", "I excel at", "I have successfully", "I can",
            "I will", "my expertise", "proven track record", "demonstrated ability"
        ]

        uncertain_phrases = [
            "I think", "I believe", "I hope", "maybe", "perhaps",
            "I would try", "I might be able", "hopefully"
        ]

        text_lower = text.lower()

        confident_count = sum(1 for phrase in confident_phrases if phrase in text_lower)
        uncertain_count = sum(1 for phrase in uncertain_phrases if phrase in text_lower)

        if confident_count > uncertain_count and confident_count > 1:
            return "Confident"
        elif uncertain_count > confident_count:
            return "Lacks Confidence"
        else:
            return "Moderate Confidence"

    def _analyze_enthusiasm(self, text: str) -> str:
        """Analyze enthusiasm level"""
        enthusiasm_words = [
            "excited", "thrilled", "passionate", "eager", "enthusiastic",
            "love", "enjoy", "fascinated", "inspired", "motivated"
        ]

        text_lower = text.lower()
        enthusiasm_count = sum(1 for word in enthusiasm_words if word in text_lower)

        if enthusiasm_count >= 3:
            return "High Enthusiasm"
        elif enthusiasm_count >= 1:
            return "Moderate Enthusiasm"
        else:
            return "Low Enthusiasm"

    def _analyze_word_variety(self, text: str) -> Dict[str, Any]:
        """Analyze vocabulary variety"""
        words = [word.lower() for word in re.findall(r'\b\w+\b', text) if len(word) > 3]

        if not words:
            return {"variety_score": 0, "unique_percentage": 0}

        unique_words = set(words)
        variety_score = len(unique_words) / len(words) * 100

        return {
            "variety_score": round(variety_score, 1),
            "unique_percentage": round(len(unique_words) / len(words) * 100, 1),
            "total_words": len(words),
            "unique_words": len(unique_words)
        }

    def _analyze_sentence_complexity(self, text: str) -> Dict[str, Any]:
        """Analyze sentence structure complexity"""
        sentences = re.split(r'[.!?]+', text)
        sentences = [s.strip() for s in sentences if s.strip()]

        if not sentences:
            return {"average_length": 0, "complexity": "Unknown"}

        sentence_lengths = [len(sentence.split()) for sentence in sentences]
        average_length = sum(sentence_lengths) / len(sentence_lengths)

        if average_length < 10:
            complexity = "Simple"
        elif average_length < 20:
            complexity = "Moderate"
        else:
            complexity = "Complex"

        return {
            "average_length": round(average_length, 1),
            "complexity": complexity,
            "sentence_count": len(sentences),
            "longest_sentence": max(sentence_lengths) if sentence_lengths else 0,
            "shortest_sentence": min(sentence_lengths) if sentence_lengths else 0
        }

    def get_improvement_suggestions(self, content: Dict[str, Any], tone_analysis: Dict[str, Any]) -> List[
        Dict[str, str]]:
        """Get specific improvement suggestions based on analysis"""
        suggestions = []

        # Tone improvements
        if tone_analysis.get('tone') == "Too Casual":
            suggestions.append({
                "category": "Tone",
                "suggestion": "Use more formal language and avoid contractions",
                "priority": "High"
            })

        if tone_analysis.get('confidence_level') == "Lacks Confidence":
            suggestions.append({
                "category": "Confidence",
                "suggestion": "Replace uncertain phrases like 'I think' with confident statements like 'I am confident'",
                "priority": "High"
            })

        if tone_analysis.get('enthusiasm_level') == "Low Enthusiasm":
            suggestions.append({
                "category": "Enthusiasm",
                "suggestion": "Add words that show genuine interest in the role, such as 'excited', 'passionate', or 'eager'",
                "priority": "Medium"
            })

        # Word variety improvements
        word_variety = tone_analysis.get('word_variety', {})
        if word_variety.get('variety_score', 0) < 60:
            suggestions.append({
                "category": "Vocabulary",
                "suggestion": "Increase vocabulary variety to avoid repetition and show communication skills",
                "priority": "Medium"
            })

        # Sentence complexity improvements
        sentence_analysis = tone_analysis.get('sentence_complexity', {})
        if sentence_analysis.get('complexity') == "Simple":
            suggestions.append({
                "category": "Writing Style",
                "suggestion": "Vary sentence length and structure to create more engaging content",
                "priority": "Low"
            })
        elif sentence_analysis.get('complexity') == "Complex":
            suggestions.append({
                "category": "Writing Style",
                "suggestion": "Simplify some sentences for better readability",
                "priority": "Medium"
            })

        return suggestions