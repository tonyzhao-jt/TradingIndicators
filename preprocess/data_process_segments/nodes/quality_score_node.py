"""
Quality Score Node - 使用LLM对description->code样本进行质量评分
"""

import json
import time
from typing import List, Dict
import requests
import os
import re
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class QualityScoreNode:
    def __init__(self):
        self.name = "quality_score_node"
        self.min_score = float(os.getenv("QUALITY_SCORE_THRESHOLD", "6.0"))  # 从环境变量读取阈值
        self.max_retries = 3
        self.retry_delay = 1
    
    def process(self, segments: List[Dict]) -> List[Dict]:
        """Process segments and filter by quality score"""
        print(f"QualityScoreNode: Processing {len(segments)} segments")
        
        scored_segments = []
        all_scores = []
        
        for i, segment in enumerate(segments):
            try:
                score = self.score_segment(segment)
                all_scores.append(score)
                
                print(f"Segment {i+1}: Score={score:.1f} - {segment['input'][:80]}...")
                
                if score >= self.min_score:
                    # Only keep input/output for final result
                    final_segment = {
                        'input': segment['input'],
                        'output': segment['output']
                    }
                    scored_segments.append(final_segment)
                    
            except Exception as e:
                print(f"Error scoring segment {i}: {e}")
                continue
        
        if all_scores:
            avg_score = sum(all_scores) / len(all_scores)
            print(f"QualityScoreNode: Average score: {avg_score:.2f}, Min threshold: {self.min_score}")
            print(f"QualityScoreNode: Score range: {min(all_scores):.1f} - {max(all_scores):.1f}")
        
        print(f"QualityScoreNode: Kept {len(scored_segments)}/{len(segments)} high-quality segments")
        return scored_segments
    
    def score_segment(self, segment: Dict) -> float:
        """Score a single segment using LLM or heuristic"""
        description = segment['input']
        code = segment['output']
        
        # Try to use LLM scoring first
        use_llm = os.getenv("USE_LLM_SCORING", "false").lower() == "true"
        
        if use_llm:
            try:
                prompt = self.create_scoring_prompt(description, code)
                score = self.call_llm_api(prompt)
                return score
            except Exception as e:
                print(f"LLM scoring failed, falling back to heuristic: {e}")
        
        # Fall back to heuristic scoring
        score = self.heuristic_score(description, code)
        return score
    
    def create_scoring_prompt(self, description: str, code: str) -> str:
        """Create scoring prompt for LLM"""
        prompt = f"""
请评估以下trading strategy代码片段的质量，从1-10分评分：

Description: {description}

Code: {code}

评分标准：
- 代码与描述的匹配度 (30%)
- 代码的技术准确性 (25%) 
- 描述的清晰度和专业性 (25%)
- 代码的实用性和可执行性 (20%)

请只返回一个1-10之间的数字分数。
        """
        return prompt
    
    def heuristic_score(self, description: str, code: str) -> float:
        """Simple heuristic scoring (replace with actual LLM call)"""
        score = 3.0  # Lower base score
        
        # Length factors (better content usually longer)
        if len(description) > 50:
            score += 1.0
        if len(description) > 100:
            score += 0.5
        if len(code) > 20:
            score += 1.0
        if len(code) > 50:
            score += 0.5
        
        # Technical content analysis
        technical_terms = ['sma', 'ema', 'rsi', 'macd', 'ta.', 'close', 'open', 'high', 'low', 'volume', 'strategy', 'input', 'threshold']
        tech_count = sum(1 for term in technical_terms if term.lower() in description.lower() or term.lower() in code.lower())
        score += min(tech_count * 0.4, 2.5)
        
        # Code quality indicators
        code_indicators = ['=', 'ta.', 'input.', 'strategy.', '(', ')', '*', '+', '-']
        code_quality = sum(1 for indicator in code_indicators if indicator in code)
        score += min(code_quality * 0.2, 1.5)
        
        # Bonus for meaningful variable names
        meaningful_vars = ['threshold', 'signal', 'entry', 'exit', 'period', 'length']
        var_bonus = sum(1 for var in meaningful_vars if var.lower() in code.lower())
        score += min(var_bonus * 0.3, 1.0)
        
        # Penalize note-only or comment-only code
        if 'note:' in code.lower() or code.strip().startswith('note'):
            score -= 2.0
        
        # Penalize very generic descriptions
        generic_phrases = ['this strategy uses', 'the strategy', 'it uses', 'based on']
        generic_count = sum(1 for phrase in generic_phrases if phrase.lower() in description.lower())
        score -= generic_count * 0.3
        
        # Bonus for specific descriptions
        specific_terms = ['200-day', 'sma', 'moving average', 'crossover', 'threshold', 'signal', 'entry', 'exit']
        specific_count = sum(1 for term in specific_terms if term.lower() in description.lower())
        score += min(specific_count * 0.2, 1.0)
        
        # Ensure score is within bounds
        return max(1.0, min(10.0, score))
    
    def call_llm_api(self, prompt: str) -> float:
        """Call actual LLM API for scoring"""
        try:
            from langchain_openai import ChatOpenAI
            
            # Get configuration
            endpoint = os.getenv("LOCAL_QWEN_ENDPOINT", "http://202.45.128.234:5788/v1/")
            model_name = os.getenv("LOCAL_QWEN_MODEL_NAME", "/nfs/whlu/models/Qwen3-Coder-30B-A3B-Instruct")
            api_key = os.getenv("LOCAL_QWEN_API_KEY", "none")
            
            # Create LLM client
            llm = ChatOpenAI(
                base_url=endpoint,
                model=model_name,
                api_key=api_key,
                temperature=0.1,
                max_tokens=10
            )
            
            # Call LLM
            response = llm.invoke(prompt)
            score_text = response.content.strip()
            
            # Extract number from response
            numbers = re.findall(r'\d+(?:\.\d+)?', score_text)
            if numbers:
                score = float(numbers[0])
                return max(1.0, min(10.0, score))  # Ensure score is in 1-10 range
            else:
                print(f"Could not extract score from LLM response: {score_text}")
                return self.heuristic_score("", "")  # Fall back to heuristic
                
        except Exception as e:
            print(f"Error calling LLM API: {e}")
            return self.heuristic_score("", "")  # Fall back to heuristic