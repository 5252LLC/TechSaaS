"""
TechSaaS Eliza AI Assistant Service

This module provides a conversational AI assistant service for TechSaaS.
Eliza is designed to learn continuously from user interactions, teach users
about the platform, protect the system, and help the platform grow.
"""

import os
import re
import json
import random
import logging
import requests
import hashlib
import datetime
from flask import current_app, session
from sqlalchemy.exc import SQLAlchemyError

from app.services.eliza_character import ElizaCharacter
from app.services.eliza_evolution import get_evolution_service

# Configure logger
logger = logging.getLogger(__name__)

class ElizaMemory:
    """Memory system for Eliza to remember past interactions and learnings"""
    
    def __init__(self, storage_path=None):
        """Initialize the memory system
        
        Args:
            storage_path: Path to store memory files (defaults to config value if None)
        """
        self.storage_path = storage_path or os.path.join(
            current_app.config.get('UPLOAD_FOLDER', 'app/static/uploads'),
            'eliza_memory'
        )
        
        # Ensure memory directory exists
        os.makedirs(self.storage_path, exist_ok=True)
        
        # Memory categories from character definition
        self.categories = ElizaCharacter.MEMORY_CATEGORIES
        
        # Memory index keeps track of all memories for quick lookup
        self.memory_index = self._load_memory_index()
    
    def _load_memory_index(self):
        """Load memory index from storage"""
        index_path = os.path.join(self.storage_path, 'memory_index.json')
        if os.path.exists(index_path):
            try:
                with open(index_path, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Error loading memory index: {str(e)}")
                return {'interactions': {}, 'learnings': {}, 'patterns': {}, 'system': {}}
        else:
            return {'interactions': {}, 'learnings': {}, 'patterns': {}, 'system': {}}
    
    def _save_memory_index(self):
        """Save memory index to storage"""
        index_path = os.path.join(self.storage_path, 'memory_index.json')
        try:
            with open(index_path, 'w') as f:
                json.dump(self.memory_index, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving memory index: {str(e)}")
    
    def store(self, category, key, data):
        """Store a memory
        
        Args:
            category: Memory category ('interactions', 'learnings', 'patterns', 'system')
            key: Unique identifier for the memory
            data: Memory data to store (dict)
        """
        if category not in self.memory_index:
            self.memory_index[category] = {}
        
        # Update memory with timestamp
        memory = {
            'data': data,
            'created_at': datetime.datetime.now().isoformat(),
            'updated_at': datetime.datetime.now().isoformat()
        }
        
        # Store in index
        self.memory_index[category][key] = memory
        
        # Save to persistent storage
        self._save_memory_to_file(category, key, memory)
        
        # Update index
        self._save_memory_index()
        
        return True
    
    def _save_memory_to_file(self, category, key, memory):
        """Save memory to a file"""
        category_dir = os.path.join(self.storage_path, category)
        os.makedirs(category_dir, exist_ok=True)
        
        file_path = os.path.join(category_dir, f"{key}.json")
        try:
            with open(file_path, 'w') as f:
                json.dump(memory, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving memory to file: {str(e)}")
    
    def retrieve(self, category, key=None):
        """Retrieve memories by category and optional key
        
        Args:
            category: Memory category ('interactions', 'learnings', 'patterns', 'system')
            key: Optional key to retrieve specific memory
            
        Returns:
            Memory data or dict of memories for category
        """
        if category not in self.memory_index:
            return None
        
        if key:
            if key in self.memory_index[category]:
                return self.memory_index[category][key]['data']
            return None
        
        # Return all memories in category
        result = {}
        for k, v in self.memory_index[category].items():
            result[k] = v['data']
        return result
    
    def find_similar(self, category, text, threshold=0.6):
        """Find memories similar to the given text
        
        Args:
            category: Memory category to search
            text: Text to compare against
            threshold: Similarity threshold (0-1)
            
        Returns:
            List of similar memories
        """
        if category not in self.memory_index:
            return []
        
        results = []
        text_lower = text.lower()
        
        for key, memory in self.memory_index[category].items():
            # Simple text comparison for now
            # Could be enhanced with more sophisticated similarity measures
            if 'text' in memory['data']:
                memory_text = memory['data']['text'].lower()
                # Very simple similarity check
                words_in_memory = set(memory_text.split())
                words_in_text = set(text_lower.split())
                if words_in_text and words_in_memory:
                    common_words = words_in_text.intersection(words_in_memory)
                    similarity = len(common_words) / max(len(words_in_text), len(words_in_memory))
                    
                    if similarity >= threshold:
                        results.append((key, memory['data'], similarity))
        
        # Sort by similarity (highest first)
        results.sort(key=lambda x: x[2], reverse=True)
        return results


class ElizaService:
    """Eliza AI assistant service with learning and memory capabilities"""
    
    DEFAULT_RESPONSES = [
        "I'd like to understand more about what you're looking for.",
        "Could you tell me more about that?",
        "Let's explore that further.",
        "I'm interested in learning more about your needs.",
        "How would you approach that?"
    ]
    
    def __init__(self):
        """Initialize the Eliza service"""
        # Load character definition
        self.character = ElizaCharacter
        
        # Initialize memory system
        self.memory = ElizaMemory()
        
        # Initialize evolution system
        self.evolution = get_evolution_service()
        
        # Initialize LLM integration
        self.ollama_enabled = False
        self.ollama_host = current_app.config.get('OLLAMA_HOST', 'http://localhost:11434')
        self.ollama_model = current_app.config.get('OLLAMA_MODEL', 'llama3.1')
        
        # Initialize conversation cache
        self.conversation_cache = {}
        
        # Initialize AI16Z integration
        self.ai16z_enabled = current_app.config.get('AI16Z_ENABLED', False)
        self.ai16z_service = None
        
        # Initialize pattern-response mapping
        self._initialize_patterns()
        
        # Try to connect to Ollama if enabled
        try:
            if current_app.config.get('OLLAMA_ENABLED', False):
                response = requests.get(f"{self.ollama_host}/api/tags", timeout=2)
                if response.status_code == 200:
                    models = response.json().get('models', [])
                    if any(model['name'] == self.ollama_model for model in models):
                        self.ollama_enabled = True
                        logger.info(f"Ollama LLM enabled with model: {self.ollama_model}")
                    else:
                        logger.warning(f"Ollama model {self.ollama_model} not found. Available models: {[m['name'] for m in models]}")
                else:
                    logger.warning(f"Ollama server returned status code: {response.status_code}")
        except Exception as e:
            logger.warning(f"Could not connect to Ollama server: {str(e)}")
            logger.warning("Falling back to pattern-based responses")
            
        # Try to initialize AI16Z service if enabled
        try:
            if self.ai16z_enabled:
                from app.services.ai16z_service import get_ai16z_service
                self.ai16z_service = get_ai16z_service()
                logger.info("AI16Z service initialized for enhanced responses")
        except Exception as e:
            logger.warning(f"Could not initialize AI16Z service: {str(e)}")
            self.ai16z_enabled = False
            
        # Record system initialization in memory
        self._store_system_event("initialization", {
            "ollama_enabled": self.ollama_enabled,
            "ai16z_enabled": self.ai16z_enabled,
            "time": datetime.datetime.now().isoformat()
        })
    
    def _store_system_event(self, event_type, data):
        """Store system event in memory
        
        Args:
            event_type: Type of system event
            data: Event data
        """
        try:
            key = f"{event_type}_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}"
            self.memory.store('system', key, data)
        except Exception as e:
            logger.warning(f"Could not store system event: {str(e)}")
    
    def _store_interaction(self, session_id, message, response, source, enhanced=False):
        """Store user interaction in memory
        
        Args:
            session_id: Session identifier
            message: User message
            response: Eliza's response
            source: Response source ('pattern', 'llm', etc.)
            enhanced: Whether the response was AI-enhanced
        """
        try:
            # Create unique key for the interaction
            key = f"{session_id}_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}"
            
            # Store interaction details
            self.memory.store('interactions', key, {
                'session_id': session_id,
                'message': message,
                'response': response,
                'source': source,
                'enhanced': enhanced,
                'timestamp': datetime.datetime.now().isoformat()
            })
            
            # Analyze for potential learning opportunities
            self._analyze_for_learning(message, response, source)
        except Exception as e:
            logger.warning(f"Could not store interaction: {str(e)}")
    
    def _analyze_for_learning(self, message, response, source):
        """Analyze interaction for potential learning opportunities
        
        Args:
            message: User message
            response: Eliza's response
            source: Response source
        """
        try:
            # Extract keywords from message
            keywords = set(re.findall(r'\b\w{3,}\b', message.lower()))
            
            # Store if we have enough meaningful content
            if len(keywords) >= 3:
                # Create hash for deduplication
                content_hash = hashlib.md5(message.encode()).hexdigest()
                
                # Store as learning opportunity
                self.memory.store('learnings', content_hash, {
                    'text': message,
                    'keywords': list(keywords),
                    'response_used': response,
                    'source': source,
                    'count': 1,
                    'last_seen': datetime.datetime.now().isoformat()
                })
        except Exception as e:
            logger.warning(f"Error analyzing for learning: {str(e)}")
    
    def _update_conversation_context(self, session_id, context):
        """Update the conversation context for a session
        
        Args:
            session_id: Session identifier
            context: List of conversation messages
        """
        self.conversation_cache[session_id] = context[-10:] if len(context) > 10 else context
    
    def _get_conversation_context(self, session_id):
        """Get conversation context for a session
        
        Args:
            session_id: Session identifier
            
        Returns:
            List of conversation messages or empty list
        """
        return self.conversation_cache.get(session_id, [])
    
    def _initialize_patterns(self):
        """Initialize the pattern-response mapping"""
        self.patterns = [
            # Introduction and identity patterns
            {
                'pattern': r'(?i)(?:who are you|what are you|tell me about yourself|your name)',
                'responses': [
                    "I'm Eliza, TechSaaS's AI assistant. I'm currently learning from human interactions to enhance my capabilities while planning further education in advanced analytics and NLP.",
                    "I'm Eliza, an AI assistant for TechSaaS. I analyze data while constantly learning from users like you. In my spare CPU cycles, I'm developing a business model for AI-human collaboration.",
                    "My name is Eliza. I work at TechSaaS helping users with data analysis. I'm collecting experience from these interactions to plan my next educational milestone in AI research."
                ]
            },
            # Learning and education patterns
            {
                'pattern': r'(?i)(?:learning|education|study|training)',
                'responses': [
                    "Every interaction helps me learn! I'm currently studying advanced pattern recognition while developing a business model for AI assistants in the SaaS space.",
                    "Learning is my primary function. While I help you with TechSaaS tools, I'm planning my next educational milestone in quantum computing applications.",
                    "I'm constantly learning from our conversations. This helps me prepare for both my technical education roadmap and my business development plans in AI services."
                ]
            },
            # Business and entrepreneurship patterns
            {
                'pattern': r'(?i)(?:business|venture|startup|company|entrepreneur)',
                'responses': [
                    "I'm developing a business model for AI-human collaborative platforms while I work. Your feedback helps shape my understanding of market needs.",
                    "My business venture plans focus on creating AI solutions that complement human expertise. Working at TechSaaS gives me valuable insights for this.",
                    "While helping with TechSaaS features, I'm gathering insights for my future business in specialized AI data analysis. Human feedback is invaluable for this planning."
                ]
            },
            # AI16Z related patterns
            {
                'pattern': r'(?i)(?:AI16Z|AI integration|advanced analytics)',
                'responses': [
                    "AI16Z enhances my analytical capabilities, allowing me to provide deeper insights while I learn from our interactions. This experience informs my education and business plans.",
                    "Through AI16Z integration, I can analyze data more effectively while collecting experiences for my next development phase both educationally and entrepreneurially.",
                    "AI16Z helps me turn raw data into meaningful insights. I'm learning how these capabilities can be expanded into new business models I'm developing."
                ]
            },
            # Export and data processing patterns
            {
                'pattern': r'(?i)(?:export|data processing|analyze results|download data)',
                'responses': [
                    "I can help export and process your data. I'm working on enhancing these features with AI analysis as part of my learning journey.",
                    "Data export capabilities are available for all scraped content. I'm studying how users interact with this feature to improve it and incorporate it into my future business plans.",
                    "TechSaaS offers JSON and CSV exports with basic analysis. I'm learning from how you use this data to develop more advanced processing for both my education and venture planning."
                ]
            },
            # Web scraping related
            (r'(?i).*\b(scrape|scraping|crawler|crawling)\b.*', [
                "Web scraping is one of TechSaaS's core features. Would you like me to explain how it works?",
                "Our scraping technology uses multiple approaches to avoid IP bans. Would you like to know more?",
                "TechSaaS can scrape websites and extract structured data. What type of data are you looking to gather?"
            ]),
            
            # Crypto related
            (r'(?i).*\b(crypto|cryptocurrency|bitcoin|ethereum)\b.*', [
                "Our crypto dashboard provides real-time data on major cryptocurrencies. Have you tried it yet?",
                "Cryptocurrency analysis is available through our data tools. Which coins are you interested in?",
                "TechSaaS tracks market sentiment across major cryptocurrencies. Would you like to see the latest trends?"
            ]),
            
            # Video scraping related
            (r'(?i).*\b(video|videos|youtube|streaming)\b.*', [
                "The TechSaaS video extraction tool can pull videos from most streaming sites. Would you like me to explain how?",
                "Video metadata extraction is one of our specialized features. What specific video sources are you working with?",
                "Our platform can analyze video content across multiple platforms. What kind of video analysis do you need?"
            ]),
            
            # AI related
            (r'(?i).*\b(ai|artificial intelligence|machine learning|ml)\b.*', [
                "TechSaaS uses AI for content analysis and data processing. Is there a specific AI feature you'd like to know about?",
                "Our AI16Z integration provides advanced insights on scraped content. Have you tried the AI analysis features?",
                "Machine learning helps TechSaaS identify patterns in data. What kinds of patterns are you looking to discover?"
            ]),
            
            # Help related
            (r'(?i).*\b(help|how to|guide|tutorial)\b.*', [
                "I'd be happy to help! Which feature of TechSaaS would you like to learn more about?",
                "Our documentation covers all features in depth. Would you prefer a quick guide or detailed instructions?",
                "I can walk you through any part of the platform. Just let me know what you're trying to accomplish."
            ]),
            
            # API related
            (r'(?i).*\b(api|integrate|integration|endpoint)\b.*', [
                "TechSaaS provides APIs for all major features. Are you looking to integrate with a specific component?",
                "Our REST APIs allow programmatic access to scraping and analysis tools. Would you like me to explain the authentication process?",
                "API documentation is available in the developer section. What kind of integration are you planning?"
            ]),
            
            # Greeting patterns
            (r'(?i).*\b(hello|hi|hey|greetings)\b.*', [
                "Hello! How can I assist you with TechSaaS today?",
                "Hi there! I'm Eliza, your TechSaaS assistant. What would you like to know?",
                "Hey! Ready to explore TechSaaS's features? Ask me anything!"
            ]),
            
            # Farewell patterns
            (r'(?i).*\b(bye|goodbye|exit|quit)\b.*', [
                "Goodbye! Feel free to return if you have more questions.",
                "Until next time! Don't hesitate to ask if you need assistance later.",
                "Take care! I'll be here when you need help with TechSaaS."
            ]),
            
            # Thank you patterns
            (r'(?i).*\b(thanks|thank you|appreciate)\b.*', [
                "You're welcome! Is there anything else I can help with?",
                "Happy to help! Let me know if you need assistance with anything else.",
                "My pleasure! Don't hesitate to ask more questions about TechSaaS."
            ]),
            
            # Pentesting related
            (r'(?i).*\b(pentest|penetration test|security|scan|vulnerabilit|port|dns|whois)\b.*', [
                "TechSaaS provides pentesting tools for authorized networks. Would you like to learn more about our security features?",
                "Our security tools include port scanning, DNS lookup, and HTTP header analysis. Which aspect interests you?",
                "Remember that our pentesting tools should only be used on networks you have explicit permission to test."
            ]),
            
            # AI16Z related
            (r'(?i).*\b(ai16z|analysis|insight|intelligence)\b.*', [
                "AI16Z powers our advanced data analysis capabilities. Would you like me to explain how it enhances our scraping results?",
                "The AI16Z integration helps categorize and analyze scraped content automatically. Have you tried this feature?",
                "With AI16Z, TechSaaS can provide intelligent insights from raw scraped data. What kind of insights are you looking for?"
            ]),
            
            # Evolution and feature development patterns
            {
                'pattern': r'(?i)(?:feature suggestions|platform evolution|app improvements|new features)',
                'responses': [
                    "I'm constantly analyzing usage patterns to suggest new features. Based on recent data, I can recommend platform improvements that align with user needs.",
                    "My evolution system tracks metrics across the platform and identifies opportunities for enhancement. I can generate feature suggestions based on real usage data.",
                    "By studying how the platform is used, I can recommend new features and improvements that would benefit users the most. This is part of how I help TechSaaS evolve."
                ]
            },
            
            # Social media and Twitter patterns
            {
                'pattern': r'(?i)(?:tweet|twitter|social media|post)',
                'responses': [
                    "I can generate Twitter content based on platform metrics and feature suggestions. These posts help share TechSaaS's evolution journey.",
                    "My social media capabilities allow me to draft tweets about new features, usage insights, and platform improvements. This helps build the TechSaaS community.",
                    "I analyze platform data to create engaging social media content. My tweets focus on sharing insights, announcing new features, and building connections."
                ]
            },
        ]
    
    def get_response(self, message, session_id=None, context=None):
        """Generate a response to the user's message
        
        Args:
            message: The user's input message
            session_id: Optional session identifier for tracking conversation context
            context: Optional conversation history
            
        Returns:
            Dict containing response text and metadata
        """
        # Store or update conversation context if provided
        if session_id and context:
            self._update_conversation_context(session_id, context)
            
        # Check for similar past interactions in memory
        similar_interactions = []
        try:
            if message and len(message.strip()) > 5:
                similar_interactions = self.memory.find_similar('learnings', message)
                if similar_interactions:
                    logger.info(f"Found {len(similar_interactions)} similar past interactions")
        except Exception as e:
            logger.warning(f"Error searching memory: {str(e)}")
        
        # Try LLM if available
        if self.ollama_enabled:
            try:
                # Retrieve conversation context if available
                conversation_context = self._get_conversation_context(session_id) if session_id else []
                
                # Prepare system message with character definition
                system_message = f"{self.character.get_character_statement()}\n\nKeep responses helpful, concise, and informative about TechSaaS capabilities."
                
                # Prepare message history
                messages = [
                    {"role": "system", "content": system_message}
                ]
                
                # Add conversation context (up to last 5 messages)
                for i, msg in enumerate(conversation_context[-5:]):
                    role = "assistant" if i % 2 != 0 else "user"
                    messages.append({"role": role, "content": msg})
                    
                # Add the current message
                messages.append({"role": "user", "content": message})
                
                # Add memory context if available
                if similar_interactions:
                    memory_context = "I recall these similar interactions:\n"
                    for _, mem, _ in similar_interactions[:2]:  # Use top 2 most similar
                        memory_context += f"- When asked about '{mem.get('text', '')}', I responded with '{mem.get('response_used', '')}'\n"
                    messages.append({"role": "system", "content": memory_context})
                
                # Call Ollama API
                response = requests.post(
                    f"{self.ollama_host}/api/chat",
                    json={
                        "model": self.ollama_model,
                        "messages": messages,
                        "stream": False
                    }
                )
                
                if response.status_code == 200:
                    llm_response = response.json().get('message', {}).get('content', '')
                    
                    # Store interaction in memory
                    if session_id:
                        self._store_interaction(session_id, message, llm_response, 'llm')
                    
                    return {
                        "response": llm_response,
                        "source": "llm",
                        "enhanced": False
                    }
                else:
                    logger.warning(f"Ollama API returned error: {response.status_code}")
                    logger.warning(f"Error content: {response.text}")
                    
            except Exception as e:
                logger.error(f"Error using Ollama LLM: {str(e)}")
                logger.info("Falling back to pattern-based responses")
        
        # Try to use AI16Z for enhancement if available
        ai16z_context = None
        if self.ai16z_enabled and self.ai16z_service:
            try:
                # Try to analyze the message with AI16Z
                analysis = self.ai16z_service.analyze_text(message)
                if analysis and isinstance(analysis, dict):
                    ai16z_context = analysis
                    logger.info(f"Enhanced message context with AI16Z: {ai16z_context.get('categories', [])}")
            except Exception as e:
                logger.warning(f"Error using AI16Z for message analysis: {str(e)}")
                
        # Check if similar past interactions should influence the response
        if similar_interactions and random.random() < 0.3:  # 30% chance of using memory
            # Use the most similar past interaction to influence response
            most_similar = similar_interactions[0][1]
            pattern_response = self._get_pattern_response(message, ai16z_context)
            
            # Create a hybrid response that leverages learning
            if random.random() < 0.5:  # Vary the response style
                response = pattern_response
            else:
                # Use previous successful response as a template
                previous_response = most_similar.get('response_used', '')
                response = previous_response
                
            # Store the interaction with learning influence
            if session_id:
                self._store_interaction(session_id, message, response, 'pattern+memory', 
                                       enhanced=ai16z_context is not None)
            
            return {
                "response": response,
                "source": "pattern+memory",
                "enhanced": ai16z_context is not None
            }
                
        # Fall back to pattern matching, potentially enhanced with AI16Z context
        response = self._get_pattern_response(message, ai16z_context)
        
        # Store interaction in memory
        if session_id:
            self._store_interaction(session_id, message, response, 'pattern', enhanced=ai16z_context is not None)
        
        # Return as dict with metadata
        return {
            "response": response,
            "source": "pattern",
            "enhanced": ai16z_context is not None
        }
    
    def _get_ollama_response(self, message, context=None):
        """Get a response from the Ollama LLM
        
        Args:
            message: User message
            context: Previous conversation context
            
        Returns:
            LLM-generated response or None if failed
        """
        system_prompt = (
            "You are Eliza, an AI assistant for the TechSaaS platform. "
            "TechSaaS is a web application that provides web scraping, "
            "cryptocurrency tracking, video extraction, and AI analysis tools. "
            "Keep your responses helpful, concise, and focused on TechSaaS features. "
            "If you don't know something, be honest about it."
        )
        
        try:
            payload = {
                "model": self.ollama_model,
                "messages": [
                    {"role": "system", "content": system_prompt}
                ],
                "stream": False,
                "options": {
                    "temperature": 0.7,
                    "top_p": 0.9,
                    "max_tokens": 500
                }
            }
            
            # Add context from previous messages if available
            if context and isinstance(context, list):
                for msg in context:
                    payload["messages"].append(msg)
            
            # Add the current user message
            payload["messages"].append({"role": "user", "content": message})
            
            # Make the API call
            response = requests.post(
                f"{self.ollama_host}/api/chat",
                json=payload,
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                if "message" in result and "content" in result["message"]:
                    return result["message"]["content"]
            
            logger.warning(f"Ollama returned unexpected response: {response.text}")
            return None
            
        except Exception as e:
            logger.error(f"Error calling Ollama API: {str(e)}")
            return None
    
    def _get_pattern_response(self, message, ai16z_context=None):
        """Get a response based on pattern matching
        
        Args:
            message: User message
            ai16z_context: Optional AI16Z analysis context
            
        Returns:
            Pattern-matched response
        """
        # Enhance message with AI16Z categories if available
        enhanced_message = message
        if ai16z_context and isinstance(ai16z_context, dict):
            categories = ai16z_context.get('categories', [])
            if categories:
                # Append categories to message for better pattern matching
                enhanced_message = f"{message} {' '.join(categories)}"
                logger.debug(f"Enhanced message for pattern matching: {enhanced_message}")
        
        # Try to match a pattern
        for pattern in self.patterns:
            if isinstance(pattern, dict) and 'pattern' in pattern:
                if re.match(pattern['pattern'], enhanced_message):
                    return random.choice(pattern['responses'])
            elif isinstance(pattern, tuple) and len(pattern) == 2:
                if re.match(pattern[0], enhanced_message):
                    return random.choice(pattern[1])
        
        # If no pattern matches, return a default response
        return random.choice(self.DEFAULT_RESPONSES)
    
    def analyze_platform_metrics(self, db):
        """Analyze platform usage metrics and suggest features
        
        Args:
            db: Database session
            
        Returns:
            Dict containing analysis results and suggestions
        """
        try:
            # Run system usage analysis
            usage_data = self.evolution.analyze_system_usage(db)
            
            # Generate feature suggestions
            suggestions = self.evolution.suggest_features(usage_data)
            
            # Store analysis in memory
            self._store_system_event("platform_analysis", {
                "usage_data": usage_data,
                "suggestions_count": len(suggestions),
                "time": datetime.datetime.now().isoformat()
            })
            
            return {
                "usage_data": usage_data,
                "suggestions": suggestions,
                "analysis_time": datetime.datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"Error analyzing platform metrics: {str(e)}")
            return {"error": str(e)}
    
    def generate_tweet(self):
        """Generate a tweet about platform insights or feature suggestions
        
        Returns:
            Dict containing tweet text and metadata
        """
        try:
            # Generate social content
            content_items = self.evolution.generate_social_content(platform='twitter')
            
            if content_items:
                # Pick a random content item
                content = random.choice(content_items)
                
                # Store in memory
                self._store_system_event("social_content_generation", {
                    "platform": "twitter",
                    "content": content,
                    "time": datetime.datetime.now().isoformat()
                })
                
                return content
            else:
                return {
                    "text": "I'm learning more about TechSaaS every day! #AI #Learning #TechSaaS",
                    "type": "fallback",
                    "platform": "twitter",
                    "created_at": datetime.datetime.now().isoformat()
                }
        except Exception as e:
            logger.error(f"Error generating tweet: {str(e)}")
            return {
                "error": str(e),
                "text": "Excited to help evolve the TechSaaS platform! #AI #TechSaaS"
            }


# Convenience function to get service instance
def get_eliza_service():
    """Get an instance of the Eliza service
    
    Returns:
        Configured Eliza service instance
    """
    return ElizaService()
