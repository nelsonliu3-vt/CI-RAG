"""
Challenge Generator Module for CI-RAG
Auto-generates tough follow-up questions to stress-test competitive insights
"""

from typing import List, Dict, Any
import random


class ChallengeGenerator:
    """Generates adversarial challenges for CI analysis"""

    # Challenge templates by perspective
    CHALLENGE_TEMPLATES = {
        "regulatory": {
            "name": "FDA/Regulatory Perspective",
            "icon": "🏛️",
            "templates": [
                "What are the regulatory risks and potential FDA concerns with {topic}? What additional data or studies might be required for approval?",
                "How does the safety profile of {topic} compare to FDA-approved standards? Are there any signals that could trigger regulatory actions?",
                "What is the likelihood of FDA requiring additional trials or post-marketing commitments for {topic}? What precedents exist?",
                "Could the trial design or endpoints for {topic} face FDA pushback? What alternative designs should be considered?",
                "What regulatory pathway challenges might {topic} face in different markets (FDA, EMA, PMDA)? How do approval requirements differ?",
                "Are there any boxed warning risks or REMS requirements that {topic} might face based on its profile?",
                "What are the chances of FDA breakthrough therapy designation for {topic}, and what impact would that have on timelines?"
            ]
        },
        "commercial": {
            "name": "Investor/Commercial Perspective",
            "icon": "💼",
            "templates": [
                "What is the realistic market size and revenue potential for {topic}? How does this compare to competitor projections?",
                "What are the reimbursement challenges and payer objections {topic} will likely face? What is the pricing strategy?",
                "How defensible is the competitive positioning of {topic}? What happens when next-gen competitors enter the market?",
                "What is the commercial risk if efficacy in real-world practice doesn't match trial results for {topic}?",
                "What are the manufacturing and supply chain risks that could impact {topic}'s commercial success?",
                "How will {topic} perform in head-to-head comparisons with established standard of care? What happens if it's only equivalent, not superior?",
                "What is the patent landscape and exclusivity timeline for {topic}? When will biosimilar or generic competition emerge?"
            ]
        },
        "scientific": {
            "name": "Scientific/Clinical Perspective",
            "icon": "🔬",
            "templates": [
                "What are the potential scientific limitations or biases in the trial data for {topic}? How robust are the results?",
                "How do the confidence intervals and p-values for {topic} hold up under scrutiny? Are the results clinically meaningful vs. just statistically significant?",
                "What patient populations or subgroups might not benefit from {topic}? Are there any negative responder segments?",
                "What is the mechanism of action risk for {topic}? Could on-target or off-target toxicities emerge with longer follow-up?",
                "How does the biomarker strategy for {topic} stand up? Is the enrichment strategy overly narrow or poorly validated?",
                "What are the durability concerns for {topic}? Do responses hold up over time, or is there evidence of resistance or relapse?",
                "What combination therapy challenges exist for {topic}? How will it fit into evolving treatment paradigms?"
            ]
        },
        "safety": {
            "name": "Safety & Risk Assessment",
            "icon": "⚠️",
            "templates": [
                "What are the most concerning adverse events for {topic}, and how do they compare to class effects vs. novel risks?",
                "What is the risk of rare but serious adverse events emerging with larger patient populations or longer follow-up for {topic}?",
                "How do dose-limiting toxicities impact the therapeutic index of {topic}? Is there enough separation between efficacy and toxicity doses?",
                "What are the drug-drug interaction risks for {topic} in real-world polypharmacy scenarios?",
                "What special populations (elderly, renal/hepatic impairment, pregnant women) face elevated safety risks with {topic}?",
                "What are the long-term safety unknowns for {topic}? Could late-emerging toxicities become an issue?",
                "How does the safety profile of {topic} impact quality of life and patient adherence?"
            ]
        },
        "strategic": {
            "name": "Strategic & Portfolio",
            "icon": "📊",
            "templates": [
                "What is the opportunity cost of pursuing {topic} vs. alternative programs or indications? How does it fit in the portfolio strategy?",
                "What are the key strategic risks if {topic} fails to differentiate sufficiently from competitors?",
                "How does {topic} perform in scenario planning? What happens in best-case, base-case, and worst-case scenarios?",
                "What partnership or licensing risks exist for {topic}? How secure are key collaborations and dependencies?",
                "What are the pivotal trial risks for {topic}? What is the probability of success, and what are the failure modes?",
                "How does the timeline for {topic} compare to competitive programs? What happens if we're second or third to market?",
                "What are the go/no-go decision criteria for advancing {topic}? At what point should the program be deprioritized?"
            ]
        }
    }

    def __init__(self):
        """Initialize challenge generator"""
        pass

    def generate_challenges(
        self,
        query: str,
        answer: str,
        sources: List[Dict[str, Any]],
        num_challenges_per_perspective: int = 2
    ) -> Dict[str, List[Dict[str, str]]]:
        """
        Generate adversarial challenges for a given Q&A

        Args:
            query: Original user query
            answer: AI-generated answer
            sources: Retrieved source documents
            num_challenges_per_perspective: Number of challenges to generate per perspective

        Returns:
            Dict mapping perspective to list of challenge questions
        """
        # Extract topic from query (simple heuristic: last few words or first noun phrase)
        topic = self._extract_topic(query)

        challenges = {}

        for perspective, config in self.CHALLENGE_TEMPLATES.items():
            perspective_challenges = []

            # Select random templates
            templates = random.sample(
                config["templates"],
                min(num_challenges_per_perspective, len(config["templates"]))
            )

            for template in templates:
                challenge_question = template.format(topic=topic)
                perspective_challenges.append({
                    "question": challenge_question,
                    "perspective": config["name"],
                    "icon": config["icon"]
                })

            challenges[perspective] = perspective_challenges

        return challenges

    def generate_targeted_challenge(
        self,
        query: str,
        answer: str,
        perspective: str
    ) -> str:
        """
        Generate a single targeted challenge for a specific perspective

        Args:
            query: Original query
            answer: AI answer
            perspective: One of: regulatory, commercial, scientific, safety, strategic

        Returns:
            Challenge question string
        """
        if perspective not in self.CHALLENGE_TEMPLATES:
            return ""

        topic = self._extract_topic(query)
        templates = self.CHALLENGE_TEMPLATES[perspective]["templates"]
        template = random.choice(templates)

        return template.format(topic=topic)

    def _extract_topic(self, query: str) -> str:
        """
        Extract topic from query for challenge generation

        Args:
            query: User's original query

        Returns:
            Topic string (drug name, program, or key phrase)
        """
        # Simple heuristic: Look for patterns like "Drug X", "competitor Y", or last 3-5 words
        query_lower = query.lower()

        # Look for drug/competitor mentions
        keywords = ["drug", "competitor", "program", "trial", "study", "compound"]
        for keyword in keywords:
            if keyword in query_lower:
                # Extract phrase after keyword
                start_idx = query_lower.find(keyword)
                phrase = query[start_idx:start_idx + 50].split(',')[0].split('.')[0].strip()
                if len(phrase) > len(keyword):
                    return phrase

        # Fallback: Use last 30 chars of query
        if len(query) > 30:
            return query[-30:].strip()
        else:
            return query.strip()


def get_challenge_generator() -> ChallengeGenerator:
    """Get challenge generator singleton"""
    return ChallengeGenerator()
