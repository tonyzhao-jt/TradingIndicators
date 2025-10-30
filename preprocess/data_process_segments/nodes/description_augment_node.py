"""
Description Augment Node - Regenerate descriptions that don't match code
"""

import json
import re
import logging
from typing import List, Dict
from llm_client import get_llm

logger = logging.getLogger(__name__)


class DescriptionAugmentNode:
    def __init__(self, match_threshold: float = 6.0):
        self.name = "description_augment_node"
        self.match_threshold = match_threshold
        self.llm_client = None
    
    def get_llm_client(self):
        """Lazy load LLM client"""
        if self.llm_client is None:
            self.llm_client = get_llm()
        return self.llm_client
    
    def check_description_code_match(self, description: str, code: str) -> Dict:
        """Check if description matches the code implementation"""
        # Handle list output
        if isinstance(code, list):
            code = '\n'.join(str(item) for item in code)
        
        prompt = f"""You are an expert code reviewer. Evaluate if the following description accurately matches the code implementation.

DESCRIPTION:
{description}

CODE:
{code}

Rate the match on a scale of 0-10 where:
- 0-3: Poor match - description and code are unrelated or very different
- 4-6: Partial match - some overlap but significant gaps or inaccuracies
- 7-10: Good match - description accurately reflects the code implementation

Return your response in JSON format:
{{
    "match_score": <number 0-10>,
    "reasoning": "<brief explanation of why they match or don't match>",
    "needs_regeneration": <true/false>
}}"""

        try:
            llm = self.get_llm_client()
            response = llm.client.chat.completions.create(
                model=llm.model,
                messages=[
                    {"role": "system", "content": "You are an expert at evaluating code documentation quality."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                max_tokens=512
            )
            
            result_text = response.choices[0].message.content.strip()
            
            # Extract JSON from response
            json_match = re.search(r'\{[^}]+\}', result_text, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group())
                return result
            else:
                logger.warning(f"Could not parse JSON from response: {result_text}")
                return {"match_score": 5, "reasoning": "Could not parse response", "needs_regeneration": False}
                
        except Exception as e:
            logger.error(f"Match check failed: {str(e)}")
            return {"match_score": 5, "reasoning": f"Error: {str(e)}", "needs_regeneration": False}
    
    def generate_new_description(self, code: str, original_description: str = "") -> str:
        """Generate a new description based on the code implementation"""
        # Handle list output
        if isinstance(code, list):
            code = '\n'.join(str(item) for item in code)
        
        # Build prompt with original description as reference
        if original_description and original_description.strip():
            prompt = f"""You are an expert at documenting trading strategy code. Write a clear, concise description of what the following code does.

ORIGINAL DESCRIPTION (for reference only - may be inaccurate or incomplete):
{original_description}

CODE:
{code}

Requirements:
1. Use the ORIGINAL DESCRIPTION as a reference to understand the intent, but base your description primarily on what the CODE actually does
2. If the original description contains useful context or terminology, incorporate it
3. Describe the technical indicators and calculations used in the code
4. Explain the trading logic or signal generation clearly
5. Mention key parameters or thresholds
6. Keep the description concise and under 1024 tokens
7. Be specific and accurate - only describe what's present in the code
8. Write in clear, professional English
9. Do not mention that this is a regenerated description

Provide only the improved description without any additional explanation or formatting."""
        else:
            prompt = f"""You are an expert at documenting trading strategy code. Write a clear, concise description of what the following code does.

CODE:
{code}

Requirements:
1. Describe the technical indicators and calculations used
2. Explain the trading logic or signal generation
3. Mention key parameters or thresholds
4. Keep the description concise and under 1024 tokens
5. Be specific and accurate - don't add information not present in the code
6. Write in clear, professional English

Provide only the description without any additional explanation or formatting."""

        try:
            llm = self.get_llm_client()
            response = llm.client.chat.completions.create(
                model=llm.model,
                messages=[
                    {"role": "system", "content": "You are an expert technical writer specializing in trading strategies and financial code documentation."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=1024
            )
            
            description = response.choices[0].message.content.strip()
            
            # Remove any markdown formatting
            description = description.replace('**', '').replace('*', '')
            description = description.strip()
            
            return description
            
        except Exception as e:
            logger.error(f"Description generation failed: {str(e)}")
            return ""
    
    def process(self, segments: List[Dict]) -> List[Dict]:
        """Process segments and augment descriptions that don't match code"""
        print(f"DescriptionAugmentNode: Processing {len(segments)} segments")
        print(f"  Match threshold: {self.match_threshold}/10")
        
        augmented_segments = []
        regenerated_count = 0
        match_scores = []
        
        for idx, segment in enumerate(segments):
            try:
                description = segment.get('input', '')
                code = segment.get('output', '')
                
                if not description or not code:
                    logger.warning(f"Segment {idx} has empty description or code, skipping")
                    augmented_segments.append(segment)
                    continue
                
                # Check if description matches code
                print(f"  Checking segment {idx + 1}/{len(segments)}...", end=' ')
                match_result = self.check_description_code_match(description, code)
                
                match_score = match_result.get('match_score', 5)
                needs_regen = match_result.get('needs_regeneration', False)
                match_scores.append(match_score)
                
                print(f"Score: {match_score}/10")
                
                # If match score is below threshold, regenerate description
                if match_score < self.match_threshold or needs_regen:
                    print(f"    → Regenerating (below threshold {self.match_threshold})")
                    new_description = self.generate_new_description(code, original_description=description)
                    
                    if new_description:
                        augmented_segment = segment.copy()
                        augmented_segment['input'] = new_description
                        augmented_segment['_original_input'] = description
                        augmented_segment['_description_regenerated'] = True
                        augmented_segment['_match_score'] = match_score
                        augmented_segment['_match_reasoning'] = match_result.get('reasoning', '')
                        
                        augmented_segments.append(augmented_segment)
                        regenerated_count += 1
                    else:
                        logger.warning(f"Failed to generate new description for segment {idx}")
                        segment['_description_augment_failed'] = True
                        augmented_segments.append(segment)
                else:
                    segment['_match_score'] = match_score
                    augmented_segments.append(segment)
                    
            except Exception as e:
                logger.error(f"Error augmenting segment {idx}: {str(e)}")
                segment['_description_augment_error'] = str(e)
                augmented_segments.append(segment)
        
        avg_match_score = sum(match_scores) / len(match_scores) if match_scores else 0
        
        print(f"DescriptionAugmentNode: Regenerated {regenerated_count}/{len(segments)} descriptions")
        print(f"  Average match score: {avg_match_score:.2f}/10")
        
        return augmented_segments
