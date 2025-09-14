Examples
========

This section provides comprehensive examples of using Deimos Router in various scenarios.

Basic Usage Example
-------------------

Here's a simple example to get you started:

.. code-block:: python

    from deimos_router import Router, register_router, chat
    from deimos_router.rules import TaskRule
    
    # Create a simple task rule
    task_rule = TaskRule(
        name="task-router",
        rules={
            "code": "openai/gpt-4o",
            "creative": "anthropic/claude-3-sonnet",
            "simple": "openai/gpt-4o-mini"
        }
    )
    
    # Create and register router
    router = Router(
        name="basic_router",
        rules=[task_rule],
        default_model="openai/gpt-4o-mini"
    )
    register_router(router)
    
    # Make a chat completion request
    response = chat.completions.create(
        model="deimos/basic_router",
        messages=[
            {"role": "user", "content": "Help me write a Python function"}
        ],
        task="code"  # This will trigger the task rule
    )
    
    print(response.choices[0].message.content)

Multi-Rule Router Example
-------------------------

This example shows how to create a router with multiple rules for different scenarios:

.. code-block:: python

    from deimos_router import Router, register_router, chat
    from deimos_router.rules import (
        TaskRule, AutoTaskRule, MessageLengthRule, 
        ConversationContextRule, CodeRule
    )
    
    # Create multiple rules
    task_rule = TaskRule(
        name="task-router",
        rules={
            "urgent": "openai/gpt-4o",
            "analysis": "openai/gpt-4o"
        }
    )
    
    auto_task_rule = AutoTaskRule(
        name="auto-task-detector",
        task_mappings={
            "coding": "openai/gpt-4o",
            "creative_writing": "anthropic/claude-3-sonnet"
        },
        default="openai/gpt-4o-mini",
        llm_model="openai/gpt-4o-mini"
    )
    
    length_rule = MessageLengthRule(
        name="length-router",
        short_threshold=100,
        long_threshold=1000,
        short_model="openai/gpt-4o-mini",
        medium_model="openai/gpt-4o",
        long_model="anthropic/claude-3-sonnet"
    )
    
    context_rule = ConversationContextRule(
        name="context-router",
        new_threshold=3,
        deep_threshold=8,
        new_model="openai/gpt-4o-mini",
        developing_model="openai/gpt-4o",
        deep_model="anthropic/claude-3-sonnet"
    )
    
    # Create router with multiple rules
    multi_router = Router(
        name="multi_rule_router",
        rules=[task_rule, auto_task_rule, length_rule, context_rule],
        default_model="openai/gpt-4o-mini"
    )
    register_router(multi_router)
    
    # Test different scenarios
    
    # 1. Urgent task
    response1 = chat.completions.create(
        model="deimos/multi_rule_router",
        messages=[{"role": "user", "content": "I need help immediately!"}],
        task="urgent"
    )
    
    # 2. Auto-detected code query
    response2 = chat.completions.create(
        model="deimos/multi_rule_router",
        messages=[{
            "role": "user", 
            "content": "def fibonacci(n):\n    # Help me complete this function"
        }]
    )
    
    # 3. Long detailed message
    long_content = "I'm working on a complex data analysis project that involves multiple datasets, statistical modeling, and machine learning algorithms. I need comprehensive guidance on the best approaches, potential pitfalls, and optimization strategies for handling large-scale data processing workflows."
    response3 = chat.completions.create(
        model="deimos/multi_rule_router",
        messages=[{"role": "user", "content": long_content}]
    )

Rule Chaining Example
---------------------

This example demonstrates how to chain rules together for sophisticated routing logic:

.. code-block:: python

    from deimos_router import Router, register_router, chat
    from deimos_router.rules import TaskRule, CodeRule, MessageLengthRule
    
    # Create chained rules
    # Create a length rule for fallback
    length_rule = MessageLengthRule(
        name="length-fallback",
        short_threshold=100,
        long_threshold=500,
        short_model="openai/gpt-4o-mini",
        medium_model="openai/gpt-4o",
        long_model="anthropic/claude-3-sonnet"
    )
    
    # Create a code rule that chains to length rule for non-code
    code_rule = CodeRule(
        name="code-detector",
        code="openai/gpt-4o",
        not_code=length_rule  # Chain to length rule if no code detected
    )
    
    # Create a task rule that chains to code rule for certain tasks
    task_rule = TaskRule(
        name="task-router",
        rules={
            "urgent": "openai/gpt-4o",
            "coding": code_rule  # Chain to code rule for coding tasks
        }
    )
    
    # Create router with rule chaining
    chained_router = Router(
        name="chained_router",
        rules=[task_rule],  # Start with task rule
        default_model="openai/gpt-4o-mini"
    )
    register_router(chained_router)
    
    # Test the chain
    test_cases = [
        # Will match task_rule for urgent
        {
            "messages": [{"role": "user", "content": "Emergency help needed!"}],
            "task": "urgent"
        },
        # Will match task_rule -> code_rule (code detected)
        {
            "messages": [{"role": "user", "content": "class MyClass:\n    def __init__(self):"}],
            "task": "coding"
        },
        # Will match task_rule -> code_rule -> length_rule (no code, medium length)
        {
            "messages": [{"role": "user", "content": "Can you explain the economic implications of artificial intelligence in modern society and how it might affect employment patterns?"}],
            "task": "coding"
        },
        # Will use default model (no task specified)
        {
            "messages": [{"role": "user", "content": "Hello, how are you?"}]
        }
    ]
    
    for i, test_case in enumerate(test_cases):
        print(f"Test case {i+1}:")
        response = chat.completions.create(
            model="deimos/chained_router",
            **test_case
        )
        print(f"Response: {response.choices[0].message.content[:100]}...")
        print()

Programming Language Specific Routing
--------------------------------------

This example shows how to route based on specific programming languages:

.. code-block:: python

    from deimos_router import Router, register_router, chat
    from deimos_router.rules import CodeLanguageRule, TaskRule
    
    # Create a rule for programming language-specific routing
    code_lang_rule = CodeLanguageRule(
        name="code-language-router",
        language_mappings={
            "python": "openai/gpt-4o",
            "javascript": "openai/gpt-4o", 
            "rust": "anthropic/claude-3-sonnet",
            "sql": "openai/gpt-4o-mini",
            "html": "openai/gpt-4o-mini",
            "css": "openai/gpt-4o-mini"
        },
        default="openai/gpt-4o-mini",
        llm_model="openai/gpt-4o-mini",
        enable_llm_fallback=True
    )
    
    # Create router
    lang_router = Router(
        name="language_router",
        rules=[code_lang_rule],
        default_model="openai/gpt-4o-mini"
    )
    register_router(lang_router)
    
    # Test different programming languages
    test_cases = [
        # Python code
        {
            "messages": [{"role": "user", "content": "def calculate_fibonacci(n):\n    if n <= 1:\n        return n\n    return calculate_fibonacci(n-1) + calculate_fibonacci(n-2)"}]
        },
        # JavaScript code
        {
            "messages": [{"role": "user", "content": "const fetchData = async () => {\n    const response = await fetch('/api/data');\n    return response.json();\n};"}]
        },
        # Rust code
        {
            "messages": [{"role": "user", "content": "fn main() {\n    let mut vec = Vec::new();\n    vec.push(1);\n    println!(\"{:?}\", vec);\n}"}]
        },
        # SQL query
        {
            "messages": [{"role": "user", "content": "SELECT users.name, COUNT(orders.id) as order_count\nFROM users\nLEFT JOIN orders ON users.id = orders.user_id\nGROUP BY users.id;"}]
        }
    ]
    
    for i, test_case in enumerate(test_cases):
        print(f"Language test {i+1}:")
        response = chat.completions.create(
            model="deimos/language_router",
            **test_case
        )
        print(f"Response: {response.choices[0].message.content[:100]}...")

Natural Language Detection Example
----------------------------------

This example shows routing based on human language detection:

.. code-block:: python

    from deimos_router import Router, register_router, chat
    from deimos_router.rules import NaturalLanguageRule
    
    # Create a rule for natural language routing
    language_rule = NaturalLanguageRule(
        name="language-router",
        language_mappings={
            "en": "openai/gpt-4o",      # English
            "es": "openai/gpt-4o",      # Spanish  
            "fr": "openai/gpt-4o",      # French
            "de": "openai/gpt-4o-mini", # German
            "it": "openai/gpt-4o-mini"  # Italian
        },
        default="openai/gpt-4o-mini",
        llm_model="openai/gpt-4o-mini"
    )
    
    # Create router
    multilang_router = Router(
        name="multilang_router",
        rules=[language_rule],
        default_model="openai/gpt-4o-mini"
    )
    register_router(multilang_router)
    
    # Test different languages
    test_messages = [
        {"role": "user", "content": "Hello, can you help me with my project?"},  # English
        {"role": "user", "content": "Hola, ¿puedes ayudarme con mi proyecto?"},  # Spanish
        {"role": "user", "content": "Bonjour, pouvez-vous m'aider avec mon projet?"},  # French
        {"role": "user", "content": "Hallo, können Sie mir bei meinem Projekt helfen?"},  # German
    ]
    
    for i, message in enumerate(test_messages):
        print(f"Language test {i+1}:")
        response = chat.completions.create(
            model="deimos/multilang_router",
            messages=[message]
        )
        print(f"Response: {response.choices[0].message.content[:100]}...")

Advanced Custom Rule Example
-----------------------------

This example shows how to create custom rules with sophisticated logic:

.. code-block:: python

    from deimos_router import Router, register_router, chat
    from deimos_router.rules.base import Rule, Decision
    from deimos_router.rules import TaskRule
    from typing import Dict, Any
    import re
    from datetime import datetime
    
    # Custom rule for time-sensitive queries
    class TimeBasedRule(Rule):
        def __init__(self, name: str, business_hours_model: str, after_hours_model: str):
            super().__init__(name)
            self.business_hours_model = business_hours_model
            self.after_hours_model = after_hours_model
        
        def evaluate(self, request_data: Dict[str, Any]) -> Decision:
            current_hour = datetime.now().hour
            
            # Business hours: 9 AM to 5 PM
            if 9 <= current_hour <= 17:
                return Decision(self.business_hours_model, trigger=f"business_hours_{current_hour}")
            else:
                return Decision(self.after_hours_model, trigger=f"after_hours_{current_hour}")
    
    # Custom rule for sentiment-based routing
    class SentimentRule(Rule):
        def __init__(self, name: str, positive_model: str, negative_model: str, neutral_model: str):
            super().__init__(name)
            self.positive_model = positive_model
            self.negative_model = negative_model
            self.neutral_model = neutral_model
            
            # Simple sentiment patterns
            self.positive_patterns = [
                r'\b(great|excellent|amazing|wonderful|fantastic|love|perfect)\b',
                r'\b(thank you|thanks|appreciate)\b',
                r'[!]{2,}',  # Multiple exclamation marks
            ]
            
            self.negative_patterns = [
                r'\b(terrible|awful|hate|horrible|worst|frustrated|angry)\b',
                r'\b(problem|issue|error|bug|broken|failed)\b',
                r'\b(help|urgent|emergency)\b',
            ]
        
        def evaluate(self, request_data: Dict[str, Any]) -> Decision:
            # Extract text from messages
            text = self._extract_text(request_data)
            
            positive_score = sum(len(re.findall(pattern, text, re.IGNORECASE)) 
                               for pattern in self.positive_patterns)
            negative_score = sum(len(re.findall(pattern, text, re.IGNORECASE)) 
                               for pattern in self.negative_patterns)
            
            if negative_score > positive_score and negative_score > 0:
                return Decision(self.negative_model, trigger="negative_sentiment")
            elif positive_score > negative_score and positive_score > 0:
                return Decision(self.positive_model, trigger="positive_sentiment")
            else:
                return Decision(self.neutral_model, trigger="neutral_sentiment")
        
        def _extract_text(self, request_data: Dict[str, Any]) -> str:
            messages = request_data.get('messages', [])
            text_parts = []
            for message in messages:
                if isinstance(message, dict) and 'content' in message:
                    content = message['content']
                    if isinstance(content, str):
                        text_parts.append(content)
            return ' '.join(text_parts)
    
    # Create custom rules
    time_rule = TimeBasedRule(
        name="time-based-router",
        business_hours_model="openai/gpt-4o",
        after_hours_model="openai/gpt-4o-mini"
    )
    
    sentiment_rule = SentimentRule(
        name="sentiment-router", 
        positive_model="anthropic/claude-3-sonnet",
        negative_model="openai/gpt-4o",
        neutral_model="openai/gpt-4o-mini"
    )
    
    # Priority task rule
    priority_rule = TaskRule(
        name="priority-router",
        rules={
            "critical": "openai/gpt-4o",
            "urgent": "openai/gpt-4o"
        }
    )
    
    # Create advanced router
    advanced_router = Router(
        name="advanced_router",
        rules=[priority_rule, sentiment_rule, time_rule],
        default_model="openai/gpt-4o-mini"
    )
    register_router(advanced_router)
    
    # Test advanced routing
    test_cases = [
        # Critical task (highest priority)
        {
            "messages": [{"role": "user", "content": "System is down!"}],
            "task": "critical"
        },
        # Negative sentiment
        {
            "messages": [{"role": "user", "content": "I'm really frustrated with this terrible bug!"}]
        },
        # Positive sentiment
        {
            "messages": [{"role": "user", "content": "This is amazing! Thank you so much!"}]
        },
        # Neutral (will use time-based routing)
        {
            "messages": [{"role": "user", "content": "What's the weather like today?"}]
        }
    ]
    
    for i, test_case in enumerate(test_cases):
        print(f"Advanced test {i+1}:")
        response = chat.completions.create(
            model="deimos/advanced_router",
            **test_case
        )
        print(f"Response: {response.choices[0].message.content[:100]}...")

Debugging and Monitoring Example
---------------------------------

This example shows how to debug routing decisions and monitor router behavior:

.. code-block:: python

    from deimos_router import Router, register_router, chat
    from deimos_router.rules import TaskRule, CodeRule, MessageLengthRule
    
    # Create rules with detailed descriptions
    task_rule = TaskRule(
        name="task-router",
        rules={
            "analysis": "openai/gpt-4o",
            "support": "openai/gpt-4o-mini"
        }
    )
    
    code_rule = CodeRule(
        name="code-detector",
        code="openai/gpt-4o",
        not_code="openai/gpt-4o-mini"
    )
    
    length_rule = MessageLengthRule(
        name="length-router",
        short_threshold=100,
        long_threshold=500,
        short_model="openai/gpt-4o-mini",
        medium_model="openai/gpt-4o",
        long_model="anthropic/claude-3-sonnet"
    )
    
    # Create router
    debug_router = Router(
        name="debug_router",
        rules=[task_rule, code_rule, length_rule],
        default_model="openai/gpt-4o-mini"
    )
    register_router(debug_router)
    
    # Test with explain=True to see routing decisions
    test_messages = [
        {"role": "user", "content": "Analyze this data for trends and patterns"}
    ]
    
    # Get routing explanation
    response = chat.completions.create(
        model="deimos/debug_router",
        messages=test_messages,
        task="analysis",
        explain=True  # This will show routing decision process
    )
    
    print("Routing Decision:")
    print(f"Selected Model: {response.model}")
    
    # Access routing metadata
    if hasattr(response, '_deimos_metadata'):
        metadata = response._deimos_metadata
        print(f"Router Used: {metadata.get('router_used')}")
        print(f"Selected Model: {metadata.get('selected_model')}")
        
        # Detailed explanation of routing decisions
        if 'explain' in metadata:
            print("\nRouting Explanation:")
            for entry in metadata['explain']:
                print(f"  Rule: {entry['rule_name']} ({entry['rule_type']})")
                print(f"  Decision: {entry['decision']}")
                print(f"  Trigger: {entry['trigger']}")
    
    print(f"\nResponse: {response.choices[0].message.content}")

Production Deployment Example
-----------------------------

This example shows a production-ready setup with error handling and monitoring:

.. code-block:: python

    import logging
    from deimos_router import Router, register_router, chat
    from deimos_router.rules import (
        TaskRule, AutoTaskRule, ConversationContextRule, 
        MessageLengthRule, CodeLanguageRule
    )
    
    # Configure logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    
    # Production rule set
    production_rules = [
        # High priority: Explicit task routing
        TaskRule(
            name="priority-router",
            rules={
                "critical": "openai/gpt-4o",
                "code_review": "openai/gpt-4o",
                "support": "openai/gpt-4o-mini"
            }
        ),
        
        # Auto-detection for programming languages
        CodeLanguageRule(
            name="code-language-router",
            language_mappings={
                "python": "openai/gpt-4o",
                "javascript": "openai/gpt-4o",
                "rust": "anthropic/claude-3-sonnet",
                "sql": "openai/gpt-4o-mini"
            },
            default=None,  # Don't route if no language detected
            llm_model="openai/gpt-4o-mini"
        ),
        
        # Context-aware routing
        ConversationContextRule(
            name="context-router",
            new_threshold=3,
            deep_threshold=8,
            new_model="openai/gpt-4o-mini",
            developing_model="openai/gpt-4o",
            deep_model="anthropic/claude-3-sonnet"
        ),
        
        # Length-based routing
        MessageLengthRule(
            name="length-router",
            short_threshold=200,
            long_threshold=1500,
            short_model="openai/gpt-4o-mini",
            medium_model="openai/gpt-4o",
            long_model="anthropic/claude-3-sonnet"
        )
    ]
    
    # Create production router
    production_router = Router(
        name="production_router",
        rules=production_rules,
        default_model="openai/gpt-4o-mini"  # Cost-effective default
    )
    
    try:
        register_router(production_router)
        logger.info("Production router registered successfully")
    except Exception as e:
        logger.error(f"Failed to register router: {e}")
        raise
    
    # Production request handler with error handling
    def handle_chat_request(messages, **kwargs):
        try:
            response = chat.completions.create(
                model="deimos/production_router",
                messages=messages,
                **kwargs
            )
            
            logger.info(f"Request processed successfully with model: {response.model}")
            return response
            
        except Exception as e:
            logger.error(f"Chat request failed: {e}")
            # Fallback to direct model call
            try:
                response = chat.completions.create(
                    model="openai/gpt-4o-mini",
                    messages=messages
                )
                logger.info("Fallback request successful")
                return response
            except Exception as fallback_error:
                logger.error(f"Fallback also failed: {fallback_error}")
                raise
    
    # Example usage
    if __name__ == "__main__":
        test_requests = [
            {
                "messages": [{"role": "user", "content": "This is a critical system issue!"}],
                "task": "critical"
            },
            {
                "messages": [{"role": "user", "content": "def process_data():\n    # help me optimize this function"}]
            },
            {
                "messages": [{"role": "user", "content": "What's the weather like today?"}]
            }
        ]
        
        for i, request in enumerate(test_requests):
            print(f"\nProcessing request {i+1}:")
            try:
                response = handle_chat_request(**request)
                print(f"Success: {response.choices[0].message.content[:100]}...")
            except Exception as e:
                print(f"Failed: {e}")

Integration with Web Framework Example
--------------------------------------

This example shows how to integrate Deimos Router with a web application:

.. code-block:: python

    from flask import Flask, request, jsonify
    from deimos_router import Router, register_router, chat
    from deimos_router.rules import TaskRule, AutoTaskRule, MessageLengthRule
    
    app = Flask(__name__)
    
    # Create web application router
    web_rules = [
        TaskRule(
            name="web-task-router",
            rules={
                "support": "openai/gpt-4o-mini",
                "sales": "openai/gpt-4o",
                "technical": "openai/gpt-4o"
            }
        ),
        AutoTaskRule(
            name="web-auto-task",
            task_mappings={
                "coding": "openai/gpt-4o"
            },
            default=None,
            llm_model="openai/gpt-4o-mini"
        ),
        MessageLengthRule(
            name="web-length-router",
            short_threshold=200,
            long_threshold=1000,
            short_model="openai/gpt-4o-mini",
            medium_model="openai/gpt-4o",
            long_model="anthropic/claude-3-sonnet"
        )
    ]
    
    web_router = Router(
        name="web_router",
        rules=web_rules,
        default_model="openai/gpt-4o-mini"
    )
    register_router(web_router)
    
    @app.route('/chat', methods=['POST'])
    def chat_endpoint():
        try:
            data = request.json
            messages = data.get('messages', [])
            task = data.get('task')
            
            # Make chat completion request
            response = chat.completions.create(
                model="deimos/web_router",
                messages=messages,
                task=task,
                max_tokens=data.get('max_tokens', 1000),
                temperature=data.get('temperature', 0.7)
            )
            
            return jsonify({
                'success': True,
                'response': response.choices[0].message.content,
                'model_used': response.model,
                'usage': response.usage.dict() if hasattr(response, 'usage') and response.usage else None
            })
            
        except Exception as e:
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500
    
    @app.route('/health', methods=['GET'])
    def health_check():
        return jsonify({'status': 'healthy', 'router': 'web_router'})
    
    if __name__ == '__main__':
        app.run(debug=True, port=5000)

These examples demonstrate the flexibility and power of Deimos Router for various use cases, from simple task-based routing to complex production deployments with error handling and monitoring.