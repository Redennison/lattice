API Reference
=============

This section provides detailed API documentation for all Deimos Router components.

Core Components
---------------

Router
~~~~~~

.. autoclass:: deimos_router.Router
   :members:
   :undoc-members:
   :show-inheritance:

The main router class that manages routing decisions and model selection.

**Constructor Parameters:**

* ``name`` (str): Unique identifier for the router
* ``rules`` (List[Rule]): List of rules to evaluate for routing decisions
* ``default_model`` (str): Model to use when no rules match
* ``description`` (str, optional): Human-readable description of the router

**Methods:**

* ``register()``: Register the router to make it available for chat completions
* ``unregister()``: Remove the router from available routers
* ``route(messages, **kwargs)``: Determine which model to use for given messages
* ``get_routing_explanation(messages, **kwargs)``: Get detailed explanation of routing decision

Chat Functions
~~~~~~~~~~~~~~

.. autofunction:: deimos_router.chat_completion

Main function for making chat completion requests through registered routers.

**Parameters:**

* ``model`` (str): Router name or direct model name
* ``messages`` (List[Dict]): Conversation messages in OpenAI format
* ``task`` (str, optional): Explicit task identifier for TaskRule routing
* ``explain`` (bool, optional): Return routing explanation along with response
* ``**kwargs``: Additional parameters passed to the underlying LLM API

**Returns:**

* ``ChatCompletion``: OpenAI-compatible response object with routing information

Rule Base Classes
-----------------

Rule
~~~~

.. autoclass:: deimos_router.rules.base.Rule
   :members:
   :undoc-members:
   :show-inheritance:

Base class for all routing rules. Custom rules should inherit from this class.

**Abstract Methods:**

* ``evaluate(request_data) -> Decision``: Evaluate the rule against request data and return a Decision

**Properties:**

* ``name`` (str): Name identifier for this rule

Decision
~~~~~~~~

.. autoclass:: deimos_router.rules.base.Decision
   :members:
   :undoc-members:
   :show-inheritance:

Represents a decision made by a rule, containing either a model name, another rule, or None.

**Constructor Parameters:**

* ``value`` (Union[str, Rule, None]): Either a model name, another Rule, or None for no decision
* ``trigger`` (str, optional): The trigger that caused this decision

**Methods:**

* ``is_model() -> bool``: Check if this decision is a model selection
* ``is_rule() -> bool``: Check if this decision points to another rule
* ``is_none() -> bool``: Check if this decision is None (no decision made)
* ``get_model() -> Optional[str]``: Get the model name if this is a model decision
* ``get_rule() -> Optional[Rule]``: Get the rule if this decision points to another rule

Built-in Rules
--------------

TaskRule
~~~~~~~~

.. autoclass:: deimos_router.rules.TaskRule
   :members:
   :undoc-members:
   :show-inheritance:

Routes requests based on explicit task metadata in the request data.

**Constructor Parameters:**

* ``name`` (str): Name identifier for this rule
* ``rules`` (Dict[str, Union[str, Rule]]): Dictionary mapping task names to models or other rules

**Example:**

.. code-block:: python

    rule = TaskRule(
        name="task_router",
        rules={
            "code": "openai/gpt-4o",
            "creative": "anthropic/claude-3-sonnet",
            "analysis": "openai/gpt-4o-mini"
        }
    )

**Methods:**

* ``add_task_rule(task, decision)``: Add a new task mapping
* ``remove_task_rule(task)``: Remove a task mapping

AutoTaskRule
~~~~~~~~~~~~

.. autoclass:: deimos_router.rules.AutoTaskRule
   :members:
   :undoc-members:
   :show-inheritance:

Automatically detects task type from conversation content using an LLM and routes accordingly.

**Constructor Parameters:**

* ``name`` (str): Name identifier for this rule
* ``triggers`` (Dict[str, Union[str, Rule]]): Dictionary mapping task names to models or rules
* ``default`` (Union[str, Rule], optional): Default model/rule when no task is detected or mapped
* ``llm_model`` (str, optional): Model used for task detection (uses config default if None)

**Example:**

.. code-block:: python

    rule = AutoTaskRule(
        name="auto_task_detector",
        triggers={
            "coding": "openai/gpt-4o",
            "creative_writing": "anthropic/claude-3-sonnet",
            "data_analysis": "openai/gpt-4o-mini"
        },
        default="openai/gpt-4o-mini",
        llm_model="openai/gpt-4o-mini"
    )

**Methods:**

* ``add_task_mapping(task, decision)``: Add a new task mapping
* ``remove_task_mapping(task)``: Remove a task mapping

NaturalLanguageRule
~~~~~~~~~~~~~~~~~~~

.. autoclass:: deimos_router.rules.NaturalLanguageRule
   :members:
   :undoc-members:
   :show-inheritance:

Routes requests based on the natural language (human language like English, Spanish, etc.) detected in the message content.

**Constructor Parameters:**

* ``name`` (str): Name identifier for this rule
* ``language_mappings`` (Dict[str, Union[str, Rule]]): Dictionary mapping 2-letter ISO language codes to models or rules
* ``default`` (Union[str, Rule], optional): Default model/rule when no language is detected or mapped
* ``llm_model`` (str, optional): Model used for language detection (uses config default if None)

**Example:**

.. code-block:: python

    rule = NaturalLanguageRule(
        name="language_router",
        language_mappings={
            "en": "openai/gpt-4o",
            "es": "openai/gpt-4o",  # Spanish
            "fr": "openai/gpt-4o",  # French
            "de": "openai/gpt-4o-mini"  # German
        },
        default="openai/gpt-4o-mini"
    )

CodeRule
~~~~~~~~

.. autoclass:: deimos_router.rules.CodeRule
   :members:
   :undoc-members:
   :show-inheritance:

Detects whether the request contains programming code and routes accordingly using regex pattern matching.

**Constructor Parameters:**

* ``name`` (str): Name identifier for this rule
* ``code`` (Union[str, Rule]): Model or rule to use when code is detected
* ``not_code`` (Union[str, Rule]): Model or rule to use when no code is detected

**Example:**

.. code-block:: python

    rule = CodeRule(
        name="code_detector",
        code="openai/gpt-4o",
        not_code="openai/gpt-4o-mini"
    )

CodeLanguageRule
~~~~~~~~~~~~~~~~

.. autoclass:: deimos_router.rules.CodeLanguageRule
   :members:
   :undoc-members:
   :show-inheritance:

Detects specific programming languages in the request content and routes based on the detected language.

**Constructor Parameters:**

* ``name`` (str): Name identifier for this rule
* ``language_mappings`` (Dict[str, Union[str, Rule]]): Dictionary mapping programming language names to models or rules
* ``default`` (Union[str, Rule], optional): Default model/rule when no language is detected or mapped
* ``llm_model`` (str, optional): Model used for LLM fallback detection (uses config default if None)
* ``enable_llm_fallback`` (bool, optional): Whether to use LLM fallback for unmapped languages (default: True)

**Supported Languages (via regex):**

* ``python``, ``javascript``, ``java``, ``cpp``, ``c``, ``csharp``, ``php``, ``ruby``, ``go``, ``rust``, ``swift``, ``kotlin``, ``sql``, ``html``, ``css``

**Example:**

.. code-block:: python

    rule = CodeLanguageRule(
        name="language_specific_router",
        language_mappings={
            "python": "openai/gpt-4o",
            "javascript": "openai/gpt-4o",
            "rust": "anthropic/claude-3-sonnet",
            "sql": "openai/gpt-4o-mini"
        },
        default="openai/gpt-4o-mini"
    )

MessageLengthRule
~~~~~~~~~~~~~~~~~

.. autoclass:: deimos_router.rules.MessageLengthRule
   :members:
   :undoc-members:
   :show-inheritance:

Routes based on the total character length of user messages in the conversation.

**Constructor Parameters:**

* ``name`` (str): Name identifier for this rule
* ``short_threshold`` (int): Character count threshold for short messages
* ``long_threshold`` (int): Character count threshold for long messages
* ``short_model`` (Union[str, Rule]): Model or rule for short messages (< short_threshold)
* ``medium_model`` (Union[str, Rule]): Model or rule for medium messages (short_threshold <= length < long_threshold)
* ``long_model`` (Union[str, Rule]): Model or rule for long messages (>= long_threshold)

**Example:**

.. code-block:: python

    rule = MessageLengthRule(
        name="length_based_router",
        short_threshold=100,
        long_threshold=1000,
        short_model="openai/gpt-4o-mini",
        medium_model="openai/gpt-4o",
        long_model="anthropic/claude-3-sonnet"
    )

**Methods:**

* ``get_thresholds() -> Dict[str, int]``: Get current thresholds
* ``update_thresholds(short_threshold, long_threshold)``: Update the length thresholds

ConversationContextRule
~~~~~~~~~~~~~~~~~~~~~~~

.. autoclass:: deimos_router.rules.ConversationContextRule
   :members:
   :undoc-members:
   :show-inheritance:

Routes based on conversation history depth and context, analyzing the number of messages in the conversation.

**Constructor Parameters:**

* ``name`` (str): Name identifier for this rule
* ``new_threshold`` (int): Message count threshold for new conversations
* ``deep_threshold`` (int): Message count threshold for deep conversations
* ``new_model`` (Union[str, Rule]): Model or rule for new conversations (< new_threshold messages)
* ``developing_model`` (Union[str, Rule]): Model or rule for developing conversations (new_threshold <= messages < deep_threshold)
* ``deep_model`` (Union[str, Rule]): Model or rule for deep conversations (>= deep_threshold messages)

**Example:**

.. code-block:: python

    rule = ConversationContextRule(
        name="context_based_router",
        new_threshold=3,
        deep_threshold=10,
        new_model="openai/gpt-4o-mini",
        developing_model="openai/gpt-4o",
        deep_model="anthropic/claude-3-sonnet"
    )

**Methods:**

* ``get_thresholds() -> Dict[str, int]``: Get current thresholds
* ``update_thresholds(new_threshold, deep_threshold)``: Update the conversation depth thresholds
* ``get_conversation_stage(request_data) -> str``: Get the conversation stage ('new', 'developing', or 'deep')

Configuration
-------------

Config
~~~~~~

.. autoclass:: deimos_router.config.Config
   :members:
   :undoc-members:
   :show-inheritance:

Configuration management for Deimos Router.

**Class Methods:**

* ``get_openai_api_key() -> str``: Get OpenAI API key from environment or secrets
* ``get_base_url() -> str``: Get API base URL (default: withmartian.com)
* ``load_secrets() -> Dict``: Load secrets from secrets.json file
* ``validate_config()``: Validate current configuration

**Environment Variables:**

* ``OPENAI_API_KEY``: OpenAI API key for LLM requests
* ``DEIMOS_BASE_URL``: Custom base URL for API requests
* ``DEIMOS_SECRETS_PATH``: Path to secrets.json file

Exceptions
----------

DeimosRouterError
~~~~~~~~~~~~~~~~~

.. autoexception:: deimos_router.DeimosRouterError

Base exception class for all Deimos Router errors.

RouterNotFoundError
~~~~~~~~~~~~~~~~~~~

.. autoexception:: deimos_router.RouterNotFoundError

Raised when attempting to use a router that hasn't been registered.

RuleEvaluationError
~~~~~~~~~~~~~~~~~~~

.. autoexception:: deimos_router.RuleEvaluationError

Raised when rule evaluation fails due to LLM API errors or invalid conditions.

ConfigurationError
~~~~~~~~~~~~~~~~~~

.. autoexception:: deimos_router.ConfigurationError

Raised when configuration is invalid or missing required values.

Type Definitions
----------------

Common type aliases and data structures used throughout the API.

**Message Format:**

.. code-block:: python

    Message = Dict[str, str]  # {"role": "user|assistant|system", "content": "..."}
    Messages = List[Message]

**Router Registration:**

.. code-block:: python

    RouterInfo = Dict[str, Any]  # {"name": str, "rules": List[Rule], "default_model": str}

**Routing Result:**

.. code-block:: python

    RoutingResult = Dict[str, Any]  # {
    #     "model": str,
    #     "rule_matched": Optional[str],
    #     "explanation": Optional[str],
    #     "confidence": Optional[float]
    # }

Utility Functions
-----------------

get_registered_routers
~~~~~~~~~~~~~~~~~~~~~~

.. autofunction:: deimos_router.get_registered_routers

Returns a list of all currently registered routers.

**Returns:**

* ``List[str]``: List of router names

**Example:**

.. code-block:: python

    routers = get_registered_routers()
    print(f"Available routers: {routers}")

clear_routers
~~~~~~~~~~~~~

.. autofunction:: deimos_router.clear_routers

Removes all registered routers. Useful for testing and cleanup.

**Example:**

.. code-block:: python

    clear_routers()  # Remove all routers

validate_messages
~~~~~~~~~~~~~~~~~

.. autofunction:: deimos_router.validate_messages

Validates message format for OpenAI compatibility.

**Parameters:**

* ``messages`` (List[Dict]): Messages to validate

**Raises:**

* ``ValueError``: If messages are not in correct format

**Example:**

.. code-block:: python

    messages = [{"role": "user", "content": "Hello"}]
    validate_messages(messages)  # Raises ValueError if invalid

Usage Patterns
--------------

**Basic Router Setup:**

.. code-block:: python

    from deimos_router import Router
    from deimos_router.rules import TaskRule, CodeRule
    
    # Create rules
    task_rule = TaskRule(
        name="task_router",
        triggers={
            "code": "openai/gpt-4o",
            "creative": "anthropic/claude-3-sonnet"
        }
    )
    
    code_rule = CodeRule(
        name="code_detector",
        code="openai/gpt-4o",
        not_code="openai/gpt-4o-mini"
    )
    
    # Create and register router
    router = Router(
        name="my_router",
        rules=[task_rule, code_rule],
        default_model="openai/gpt-4o-mini"
    )
    router.register()

**Making Requests:**

.. code-block:: python

    import openai
    
    client = openai.OpenAI(
        base_url="https://api.withmartian.com/v1",
        api_key="your-key"
    )
    
    response = client.chat.completions.create(
        model="my_router",
        messages=[{"role": "user", "content": "Help with Python"}],
        task="code"
    )

**Error Handling:**

.. code-block:: python

    from deimos_router import RouterNotFoundError, RuleEvaluationError
    
    try:
        response = client.chat.completions.create(
            model="nonexistent_router",
            messages=[{"role": "user", "content": "Hello"}]
        )
    except RouterNotFoundError:
        print("Router not found, using fallback")
        response = client.chat.completions.create(
            model="openai/gpt-4o-mini",
            messages=[{"role": "user", "content": "Hello"}]
        )
    except RuleEvaluationError as e:
        print(f"Rule evaluation failed: {e}")

**Custom Rule Development:**

.. code-block:: python

    from deimos_router.rules.base import Rule, Decision
    from typing import Dict, Any
    
    class CustomRule(Rule):
        def __init__(self, name: str, custom_param: str):
            super().__init__(name)
            self.custom_param = custom_param
        
        def evaluate(self, request_data: Dict[str, Any]) -> Decision:
            # Custom routing logic
            if self._evaluate_custom_condition(request_data):
                return Decision("openai/gpt-4o", trigger="custom_condition_met")
            return Decision(None)
        
        def _evaluate_custom_condition(self, request_data: Dict[str, Any]) -> bool:
            # Implementation details
            pass

**Advanced Rule Combinations:**

.. code-block:: python

    from deimos_router.rules import (
        CodeLanguageRule, MessageLengthRule, ConversationContextRule
    )
    
    # Language-specific routing
    lang_rule = CodeLanguageRule(
        name="lang_router",
        language_mappings={
            "python": "openai/gpt-4o",
            "javascript": "openai/gpt-4o",
            "rust": "anthropic/claude-3-sonnet"
        }
    )
    
    # Length-based routing
    length_rule = MessageLengthRule(
        name="length_router",
        short_threshold=200,
        long_threshold=2000,
        short_model="openai/gpt-4o-mini",
        medium_model="openai/gpt-4o",
        long_model="anthropic/claude-3-sonnet"
    )
    
    # Context-aware routing
    context_rule = ConversationContextRule(
        name="context_router",
        new_threshold=3,
        deep_threshold=8,
        new_model="openai/gpt-4o-mini",
        developing_model="openai/gpt-4o",
        deep_model="anthropic/claude-3-sonnet"
    )

This API reference provides comprehensive and accurate documentation for all components of Deimos Router, enabling developers to effectively integrate and extend the routing system.