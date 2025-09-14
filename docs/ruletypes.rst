Rule Types
==========

Deimos Router provides several built-in rule types that you can use to implement sophisticated routing logic. Each rule type is designed for specific use cases and can be combined to create complex routing strategies.

TaskRule
--------

The ``TaskRule`` routes based on explicit task metadata in the request data.

.. code-block:: python

    from deimos_router.rules import TaskRule
    
    # Create a task rule that maps tasks to models
    task_rule = TaskRule(
        name="task-router",
        rules={
            "coding": "openai/gpt-4o",
            "creative": "anthropic/claude-3-sonnet",
            "analysis": "openai/gpt-4o-mini"
        }
    )
    
    # Usage in API call:
    # chat.completions.create(
    #     model="deimos/my-router",
    #     messages=[...],
    #     task="coding"  # This triggers the TaskRule
    # )

**Constructor Parameters:**
- ``name`` (str): Name identifier for this rule
- ``rules`` (Dict[str, Union[str, Rule]]): Dictionary mapping task names to models or other rules

**Use Cases:**
- Explicit task-based routing
- Feature flags and A/B testing
- Direct model selection based on task type

AutoTaskRule
------------

The ``AutoTaskRule`` automatically detects task type from conversation content using an LLM.

.. code-block:: python

    from deimos_router.rules import AutoTaskRule
    
    # Create an auto task rule that detects tasks automatically
    auto_task_rule = AutoTaskRule(
        name="auto-task-detector",
        task_mappings={
            "coding": "openai/gpt-4o",
            "creative_writing": "anthropic/claude-3-sonnet",
            "data_analysis": "openai/gpt-4o-mini"
        },
        default="openai/gpt-4o-mini",
        llm_model="openai/gpt-4o-mini"
    )
    
    # No explicit task parameter needed - the rule analyzes content automatically

**Constructor Parameters:**
- ``name`` (str): Name identifier for this rule
- ``task_mappings`` (Dict[str, Union[str, Rule]]): Dictionary mapping task names to models or rules
- ``default`` (Union[str, Rule], optional): Default model/rule when no task is detected
- ``llm_model`` (str, optional): Model used for task detection

**Use Cases:**
- Automatic content classification
- Smart routing without explicit task parameters
- Content-aware model selection

NaturalLanguageRule
-------------------

The ``NaturalLanguageRule`` routes based on the natural language (human language like English, Spanish, etc.) detected in the message content.

.. code-block:: python

    from deimos_router.rules import NaturalLanguageRule
    
    # Create a rule that routes based on detected human language
    language_rule = NaturalLanguageRule(
        name="language-router",
        language_mappings={
            "en": "openai/gpt-4o",      # English
            "es": "openai/gpt-4o",      # Spanish
            "fr": "openai/gpt-4o",      # French
            "de": "openai/gpt-4o-mini"  # German
        },
        default="openai/gpt-4o-mini",
        llm_model="openai/gpt-4o-mini"
    )
    
    # The rule uses an LLM to detect the language of the conversation

**Constructor Parameters:**
- ``name`` (str): Name identifier for this rule
- ``language_mappings`` (Dict[str, Union[str, Rule]]): Dictionary mapping 2-letter ISO language codes to models or rules
- ``default`` (Union[str, Rule], optional): Default model/rule when no language is detected
- ``llm_model`` (str, optional): Model used for language detection

**Use Cases:**
- Multi-language support with language-specific models
- Routing based on user's preferred language
- Internationalization and localization

CodeRule
--------

The ``CodeRule`` detects whether the request contains programming code and routes accordingly.

.. code-block:: python

    from deimos_router.rules import CodeRule
    
    # Create a rule for code detection
    code_rule = CodeRule(
        name="code-detector",
        code="openai/gpt-4o",           # Model for code-related requests
        not_code="openai/gpt-4o-mini"   # Model for non-code requests
    )
    
    # The rule uses regex patterns to detect code in messages

**Constructor Parameters:**
- ``name`` (str): Name identifier for this rule
- ``code`` (Union[str, Rule]): Model or rule to use when code is detected
- ``not_code`` (Union[str, Rule]): Model or rule to use when no code is detected

**Use Cases:**
- Routing programming questions to specialized models
- Code review and analysis workflows
- Technical vs. non-technical content separation

CodeLanguageRule
----------------

The ``CodeLanguageRule`` detects specific programming languages and routes based on the detected language.

.. code-block:: python

    from deimos_router.rules import CodeLanguageRule
    
    # Create a rule for programming language-specific routing
    code_lang_rule = CodeLanguageRule(
        name="code-language-router",
        language_mappings={
            "python": "openai/gpt-4o",
            "javascript": "openai/gpt-4o",
            "rust": "anthropic/claude-3-sonnet",
            "sql": "openai/gpt-4o-mini"
        },
        default="openai/gpt-4o-mini",
        llm_model="openai/gpt-4o-mini",
        enable_llm_fallback=True
    )
    
    # Uses regex patterns for common languages, LLM fallback for others

**Constructor Parameters:**
- ``name`` (str): Name identifier for this rule
- ``language_mappings`` (Dict[str, Union[str, Rule]]): Dictionary mapping programming language names to models or rules
- ``default`` (Union[str, Rule], optional): Default model/rule when no language is detected
- ``llm_model`` (str, optional): Model used for LLM fallback detection
- ``enable_llm_fallback`` (bool, optional): Whether to use LLM fallback for unmapped languages

**Supported Languages (via regex):**
python, javascript, java, cpp, c, csharp, php, ruby, go, rust, swift, kotlin, sql, html, css

**Use Cases:**
- Language-specific code assistance
- Routing to models specialized for certain programming languages
- Technical documentation and debugging assistance

MessageLengthRule
-----------------

The ``MessageLengthRule`` routes based on the total character length of user messages.

.. code-block:: python

    from deimos_router.rules import MessageLengthRule
    
    # Create a rule based on message length
    length_rule = MessageLengthRule(
        name="length-based-router",
        short_threshold=100,
        long_threshold=1000,
        short_model="openai/gpt-4o-mini",    # < 100 chars
        medium_model="openai/gpt-4o",        # 100-999 chars
        long_model="anthropic/claude-3-sonnet"  # >= 1000 chars
    )
    
    # Routes based on total character count of user messages

**Constructor Parameters:**
- ``name`` (str): Name identifier for this rule
- ``short_threshold`` (int): Character count threshold for short messages
- ``long_threshold`` (int): Character count threshold for long messages
- ``short_model`` (Union[str, Rule]): Model for short messages
- ``medium_model`` (Union[str, Rule]): Model for medium messages
- ``long_model`` (Union[str, Rule]): Model for long messages

**Use Cases:**
- Cost optimization by using smaller models for short queries
- Performance optimization based on input complexity
- Routing detailed queries to more capable models

ConversationContextRule
-----------------------

The ``ConversationContextRule`` routes based on conversation history depth and context.

.. code-block:: python

    from deimos_router.rules import ConversationContextRule
    
    # Create a rule based on conversation depth
    context_rule = ConversationContextRule(
        name="context-based-router",
        new_threshold=3,
        deep_threshold=10,
        new_model="openai/gpt-4o-mini",        # < 3 messages
        developing_model="openai/gpt-4o",      # 3-9 messages
        deep_model="anthropic/claude-3-sonnet" # >= 10 messages
    )
    
    # Routes based on the number of messages in the conversation

**Constructor Parameters:**
- ``name`` (str): Name identifier for this rule
- ``new_threshold`` (int): Message count threshold for new conversations
- ``deep_threshold`` (int): Message count threshold for deep conversations
- ``new_model`` (Union[str, Rule]): Model for new conversations
- ``developing_model`` (Union[str, Rule]): Model for developing conversations
- ``deep_model`` (Union[str, Rule]): Model for deep conversations

**Use Cases:**
- Escalating to more powerful models for complex conversations
- Context-aware routing based on conversation state
- Dynamic model selection based on conversation complexity

Rule Chaining and Composition
-----------------------------

Rules can be chained together by having one rule return another rule instead of a model:

.. code-block:: python

    from deimos_router.rules import TaskRule, CodeRule, MessageLengthRule
    
    # Create a chain: TaskRule -> CodeRule -> MessageLengthRule
    length_rule = MessageLengthRule(
        name="length-fallback",
        short_threshold=100,
        long_threshold=500,
        short_model="openai/gpt-4o-mini",
        medium_model="openai/gpt-4o",
        long_model="anthropic/claude-3-sonnet"
    )
    
    code_rule = CodeRule(
        name="code-detector",
        code="openai/gpt-4o",
        not_code=length_rule  # Chain to length rule if no code
    )
    
    task_rule = TaskRule(
        name="task-router",
        rules={
            "urgent": "openai/gpt-4o",
            "coding": code_rule  # Chain to code rule for coding tasks
        }
    )

**Rule Evaluation Process:**
1. Rules are evaluated in the order they appear in the router's rule list
2. Each rule returns a Decision containing either a model name or another rule
3. If a rule returns another rule, that rule is evaluated next
4. The process continues until a model name is found
5. If no rules match, the router's default model is used

Custom Rules
------------

You can create custom rules by inheriting from the base ``Rule`` class:

.. code-block:: python

    from deimos_router.rules.base import Rule, Decision
    from typing import Dict, Any
    
    class CustomRule(Rule):
        def __init__(self, name: str, custom_param: str):
            super().__init__(name)
            self.custom_param = custom_param
        
        def evaluate(self, request_data: Dict[str, Any]) -> Decision:
            # Implement your custom routing logic here
            if self._check_custom_condition(request_data):
                return Decision("openai/gpt-4o", trigger="custom_condition_met")
            return Decision(None)  # No decision made
        
        def _check_custom_condition(self, request_data: Dict[str, Any]) -> bool:
            # Your custom logic implementation
            messages = request_data.get('messages', [])
            # Analyze messages and return True/False
            return len(messages) > 5  # Example condition

**Custom Rule Guidelines:**
- Inherit from ``Rule`` base class
- Implement the ``evaluate`` method that returns a ``Decision``
- Use ``Decision(model_name, trigger)`` to return a model
- Use ``Decision(None)`` when the rule doesn't match
- Consider performance implications of your routing logic
- Test your custom rules thoroughly

Best Practices
--------------

1. **Rule Ordering**: Place more specific rules before general ones in your router
2. **Performance**: Simple rules (TaskRule, MessageLengthRule) are faster than LLM-based rules
3. **Fallbacks**: Always provide fallback logic or default models
4. **Testing**: Use the ``explain=True`` parameter to debug rule behavior
5. **Composition**: Combine simple rules rather than creating complex single rules
6. **Caching**: Consider caching for expensive rule evaluations (LLM-based rules)