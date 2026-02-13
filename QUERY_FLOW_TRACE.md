# Query Processing Flow: Frontend to Backend

Complete trace of how a user query is processed through the RAG chatbot system.

---

## 🎯 Overview Flow

```
User Input → Frontend JS → FastAPI Backend → RAG System →
Vector Search → Claude API (with Tools) → Tool Execution →
Vector Search → Claude Response → Backend → Frontend → UI Display
```

---

## 📱 Phase 1: Frontend - User Interaction

### File: [frontend/script.js](frontend/script.js)

**1. User Types Query & Clicks Send** (Lines 45-96)
```javascript
async function sendMessage() {
    const query = chatInput.value.trim();  // Get user input

    // UI Updates
    chatInput.disabled = true;  // Disable input during processing
    addMessage(query, 'user');  // Display user message
    const loadingMessage = createLoadingMessage();  // Show loading indicator
```

**2. HTTP Request to Backend** (Lines 63-72)
```javascript
    const response = await fetch(`${API_URL}/query`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            query: query,                    // User's question
            session_id: currentSessionId     // For conversation history
        })
    });
```

**3. Handle Response** (Lines 76-85)
```javascript
    const data = await response.json();
    // Response structure:
    // {
    //   answer: "Claude's response text",
    //   sources: ["Course 1 - Lesson 2", ...],
    //   session_id: "abc-123"
    // }

    loadingMessage.remove();  // Remove loading animation
    addMessage(data.answer, 'assistant', data.sources);  // Display response
```

---

## 🚀 Phase 2: Backend - API Endpoint

### File: [backend/app.py](backend/app.py)

**4. FastAPI Receives Request** (Lines 56-74)
```python
@app.post("/api/query", response_model=QueryResponse)
async def query_documents(request: QueryRequest):
    # Request model:
    # - query: str (user's question)
    # - session_id: Optional[str]

    # Create new session if none exists
    session_id = request.session_id
    if not session_id:
        session_id = rag_system.session_manager.create_session()

    # Process query through RAG system
    answer, sources = rag_system.query(request.query, session_id)

    # Return response
    return QueryResponse(
        answer=answer,
        sources=sources,
        session_id=session_id
    )
```

---

## 🧠 Phase 3: RAG System - Query Processing

### File: [backend/rag_system.py](backend/rag_system.py)

**5. RAG System Orchestrates Query** (Lines 102-140)
```python
def query(self, query: str, session_id: Optional[str] = None) -> Tuple[str, List[str]]:
    # Build prompt
    prompt = f"""Answer this question about course materials: {query}"""

    # Get conversation history from session
    history = None
    if session_id:
        history = self.session_manager.get_conversation_history(session_id)
        # Format: "User: previous question\nAssistant: previous answer\n..."

    # Generate response using AI with tools
    response = self.ai_generator.generate_response(
        query=prompt,
        conversation_history=history,
        tools=self.tool_manager.get_tool_definitions(),  # Available tools
        tool_manager=self.tool_manager                    # Tool executor
    )

    # Extract sources from last tool execution
    sources = self.tool_manager.get_last_sources()
    self.tool_manager.reset_sources()

    # Update conversation history
    if session_id:
        self.session_manager.add_exchange(session_id, query, response)

    return response, sources
```

---

## 🤖 Phase 4: AI Generator - Claude API Call

### File: [backend/ai_generator.py](backend/ai_generator.py)

**6. Prepare Claude API Call** (Lines 43-80)
```python
def generate_response(self, query: str, conversation_history: Optional[str] = None,
                     tools: Optional[List] = None, tool_manager=None) -> str:

    # Build system prompt with conversation history
    system_content = (
        f"{self.SYSTEM_PROMPT}\n\nPrevious conversation:\n{conversation_history}"
        if conversation_history
        else self.SYSTEM_PROMPT
    )

    # Prepare API parameters
    api_params = {
        "model": self.model,              # e.g., "claude-sonnet-4-5-20250929"
        "temperature": 0,
        "max_tokens": 800,
        "messages": [{"role": "user", "content": query}],
        "system": system_content,
        "tools": tools,                   # Tool definitions
        "tool_choice": {"type": "auto"}   # Let Claude decide when to use tools
    }

    # Call Claude API
    response = self.client.messages.create(**api_params)
```

**7. Claude's Response - Two Possible Paths**

### Path A: Direct Answer (No Tool Use)
```python
    # If Claude answers directly without using tools
    if response.stop_reason != "tool_use":
        return response.content[0].text
```

### Path B: Tool Use (Vector Search) ✅ Most Common
```python
    # If Claude decides to use the search tool
    if response.stop_reason == "tool_use" and tool_manager:
        return self._handle_tool_execution(response, api_params, tool_manager)
```

---

## 🔍 Phase 5: Tool Execution - Vector Search

### File: [backend/ai_generator.py](backend/ai_generator.py) (Lines 89-135)

**8. Execute Tool Call**
```python
def _handle_tool_execution(self, initial_response, base_params, tool_manager):
    # Claude's response contains tool use requests:
    # {
    #   "type": "tool_use",
    #   "id": "toolu_123",
    #   "name": "search_course_content",
    #   "input": {
    #     "query": "what is RAG",
    #     "course_name": "MCP",
    #     "lesson_number": 3
    #   }
    # }

    messages = base_params["messages"].copy()
    messages.append({"role": "assistant", "content": initial_response.content})

    # Execute all tool calls
    tool_results = []
    for content_block in initial_response.content:
        if content_block.type == "tool_use":
            # Execute the tool
            tool_result = tool_manager.execute_tool(
                content_block.name,      # "search_course_content"
                **content_block.input    # query, course_name, lesson_number
            )

            tool_results.append({
                "type": "tool_result",
                "tool_use_id": content_block.id,
                "content": tool_result   # Search results as text
            })

    # Add tool results to conversation
    messages.append({"role": "user", "content": tool_results})
```

### File: [backend/search_tools.py](backend/search_tools.py) (Lines 52-86)

**9. CourseSearchTool Executes**
```python
def execute(self, query: str, course_name: Optional[str] = None,
           lesson_number: Optional[int] = None) -> str:

    # Call vector store search
    results = self.store.search(
        query=query,
        course_name=course_name,
        lesson_number=lesson_number
    )

    # Handle errors or empty results
    if results.error:
        return results.error
    if results.is_empty():
        return f"No relevant content found."

    # Format results with course context
    return self._format_results(results)
    # Returns: "[Course Title - Lesson 2]\nLesson content here...\n\n[Course Title - Lesson 3]\n..."
```

---

## 🗄️ Phase 6: Vector Store - Semantic Search

### File: [backend/vector_store.py](backend/vector_store.py) (Lines 61-100)

**10. Vector Search Execution**
```python
def search(self, query: str, course_name: Optional[str] = None,
          lesson_number: Optional[int] = None) -> SearchResults:

    # Step 1: Resolve course name if provided (semantic matching)
    course_title = None
    if course_name:
        # Searches course_catalog collection to find matching course
        # E.g., "MCP" → "MCP: Build Rich-Context AI Apps with Anthropic"
        course_title = self._resolve_course_name(course_name)
        if not course_title:
            return SearchResults.empty(f"No course found matching '{course_name}'")

    # Step 2: Build metadata filters
    filter_dict = self._build_filter(course_title, lesson_number)
    # E.g., {"course_title": "MCP: ...", "lesson_number": 3}

    # Step 3: Query ChromaDB with embeddings
    results = self.course_content.query(
        query_texts=[query],           # Convert to embedding via sentence-transformers
        n_results=self.max_results,    # Default 5
        where=filter_dict              # Filter by course/lesson
    )
    # ChromaDB returns:
    # - documents: List of text chunks
    # - metadatas: List of metadata dicts
    # - distances: Similarity scores

    return SearchResults.from_chroma(results)
```

**How ChromaDB Search Works:**
1. **Query Embedding**: `query` text → vector (384 dimensions for all-MiniLM-L6-v2)
2. **Similarity Search**: Compare query vector to all stored chunk vectors
3. **Filtering**: Apply course_title and lesson_number filters
4. **Ranking**: Return top N most similar chunks
5. **Results**: Text chunks with metadata (course, lesson, etc.)

---

## 🎨 Phase 7: Result Formatting

### File: [backend/search_tools.py](backend/search_tools.py) (Lines 88-114)

**11. Format Search Results**
```python
def _format_results(self, results: SearchResults) -> str:
    formatted = []
    sources = []  # Track for UI display

    for doc, meta in zip(results.documents, results.metadata):
        course_title = meta.get('course_title', 'unknown')
        lesson_num = meta.get('lesson_number')

        # Build context header
        header = f"[{course_title}"
        if lesson_num is not None:
            header += f" - Lesson {lesson_num}"
        header += "]"

        # Track source for UI
        source = course_title
        if lesson_num is not None:
            source += f" - Lesson {lesson_num}"
        sources.append(source)

        formatted.append(f"{header}\n{doc}")

    # Store sources for later retrieval
    self.last_sources = sources

    # Return formatted results as single string
    return "\n\n".join(formatted)
```

**Example Output:**
```
[MCP: Build Rich-Context AI Apps with Anthropic - Lesson 3]
RAG stands for Retrieval-Augmented Generation. It's a technique that combines...

[Introduction to AI - Lesson 2]
Retrieval-Augmented Generation enhances AI responses by retrieving relevant...
```

---

## 🔄 Phase 8: Second Claude API Call

### File: [backend/ai_generator.py](backend/ai_generator.py) (Lines 126-135)

**12. Send Tool Results Back to Claude**
```python
    # Conversation now looks like:
    # [
    #   {"role": "user", "content": "What is RAG?"},
    #   {"role": "assistant", "content": [{"type": "tool_use", ...}]},
    #   {"role": "user", "content": [{"type": "tool_result", "content": "...search results..."}]}
    # ]

    # Prepare final API call (without tools this time)
    final_params = {
        "model": self.model,
        "temperature": 0,
        "max_tokens": 800,
        "messages": messages,     # Full conversation with tool results
        "system": system_content
    }

    # Get final response from Claude
    final_response = self.client.messages.create(**final_params)
    return final_response.content[0].text
    # Claude synthesizes search results into a natural answer
```

---

## 📤 Phase 9: Response Flow Back

**13. Response Travels Back Up the Stack**

[backend/ai_generator.py](backend/ai_generator.py) → Returns synthesized answer text
↓
[backend/rag_system.py](backend/rag_system.py) → Extracts sources, updates history, returns (answer, sources)
↓
[backend/app.py](backend/app.py) → Wraps in QueryResponse JSON
↓
HTTP Response → `{"answer": "...", "sources": [...], "session_id": "..."}`
↓
[frontend/script.js](frontend/script.js) → Receives JSON, displays answer and sources
↓
**User sees the answer!** 🎉

---

## 🔄 Complete Example Trace

### User Query: "What is RAG in the MCP course?"

**Step-by-Step:**

1. **Frontend**: User types "What is RAG in the MCP course?" → Click send
2. **Frontend**: POST to `/api/query` with `{query: "What is RAG in the MCP course?", session_id: "abc123"}`
3. **Backend API**: Receives request → Calls `rag_system.query()`
4. **RAG System**:
   - Retrieves conversation history for session "abc123"
   - Calls `ai_generator.generate_response()` with tools
5. **Claude API (First Call)**:
   - System prompt: "You are an AI assistant..."
   - User message: "Answer this question about course materials: What is RAG in the MCP course?"
   - Tools: Available tool definitions
   - Claude decides: "I should search for this"
   - Response: `{"type": "tool_use", "name": "search_course_content", "input": {"query": "RAG", "course_name": "MCP"}}`
6. **Tool Execution**:
   - `ToolManager.execute_tool("search_course_content", query="RAG", course_name="MCP")`
   - `CourseSearchTool.execute()` called
7. **Vector Search**:
   - Resolve "MCP" → "MCP: Build Rich-Context AI Apps with Anthropic"
   - Build filter: `{"course_title": "MCP: Build Rich-Context AI Apps with Anthropic"}`
   - Query ChromaDB with "RAG" embedding + filter
   - Returns top 5 matching chunks from MCP course
8. **Format Results**:
   - Formats chunks with headers: `"[MCP: ... - Lesson 3]\nRAG is a technique..."`
   - Tracks sources: `["MCP: ... - Lesson 3", "MCP: ... - Lesson 4"]`
9. **Claude API (Second Call)**:
   - Messages include tool results with search content
   - Claude synthesizes: "RAG (Retrieval-Augmented Generation) is a technique..."
10. **Response Assembly**:
    - RAG System extracts sources from tool
    - Updates conversation history
    - Returns: `("RAG is a technique...", ["MCP: ... - Lesson 3", ...])`
11. **Backend API**: Wraps in JSON: `{"answer": "RAG is...", "sources": [...], "session_id": "abc123"}`
12. **Frontend**: Displays answer with collapsible sources section
13. **User**: Sees formatted answer with markdown and clickable sources! ✅

---

## 🏗️ Architecture Summary

### Component Responsibilities

| Component | File | Responsibility |
|-----------|------|----------------|
| **Frontend UI** | [frontend/index.html](frontend/index.html) | Chat interface, input fields, display |
| **Frontend Logic** | [frontend/script.js](frontend/script.js) | Event handling, API calls, rendering |
| **API Layer** | [backend/app.py](backend/app.py) | REST endpoints, request/response handling |
| **RAG Orchestrator** | [backend/rag_system.py](backend/rag_system.py) | Coordinates all components, session management |
| **AI Generator** | [backend/ai_generator.py](backend/ai_generator.py) | Claude API interaction, tool execution flow |
| **Search Tools** | [backend/search_tools.py](backend/search_tools.py) | Tool definitions, search execution, formatting |
| **Vector Store** | [backend/vector_store.py](backend/vector_store.py) | ChromaDB interface, semantic search |
| **Session Manager** | [backend/session_manager.py](backend/session_manager.py) | Conversation history tracking |
| **Document Processor** | [backend/document_processor.py](backend/document_processor.py) | Parse docs, create chunks, extract metadata |
| **Data Models** | [backend/models.py](backend/models.py) | Pydantic models (Course, Lesson, Chunk) |
| **Configuration** | [backend/config.py](backend/config.py) | Settings and constants |

### Data Flow Patterns

**1. Request Flow**: User → Frontend → API → RAG → AI → Tools → Vector Store
**2. Response Flow**: Vector Store → Tools → AI → RAG → API → Frontend → User
**3. State Management**: Session Manager maintains conversation history across queries
**4. Tool Execution**: Claude decides when to search, executes tools, synthesizes results

### Key Technologies

- **Frontend**: Vanilla JavaScript, Marked.js (markdown rendering)
- **Backend**: FastAPI (Python web framework)
- **AI**: Anthropic Claude API (with tool use)
- **Vector DB**: ChromaDB (persistent vector storage)
- **Embeddings**: Sentence Transformers (all-MiniLM-L6-v2)
- **Document Processing**: Custom chunking with overlap

---

## 🎯 Performance Characteristics

### Latency Breakdown (Typical Query)

1. Frontend processing: ~10ms
2. Network request: ~20-50ms
3. Backend processing: ~5ms
4. First Claude API call: ~1-2s
5. Vector search: ~50-200ms
6. Second Claude API call: ~2-3s
7. Response assembly: ~5ms
8. Network response: ~20-50ms
9. Frontend rendering: ~10ms

**Total: ~3.5-5.5 seconds** (mostly Claude API calls)

### Optimization Opportunities

- **Caching**: Cache frequent queries
- **Parallel Processing**: Pre-compute embeddings
- **Streaming**: Stream Claude responses for faster perceived performance
- **Result Limiting**: Adjust `MAX_RESULTS` based on quality vs speed tradeoff
- **Tool Strategy**: Direct search for simple queries (bypass first Claude call)

---

## 🔐 Security & Best Practices

### Current Implementation

✅ **CORS enabled** for cross-origin requests
✅ **API key stored** in environment variables
✅ **Session management** prevents history mixing
✅ **Input validation** via Pydantic models
✅ **Error handling** at each layer

### Production Considerations

⚠️ **CORS**: Currently allows all origins (`allow_origins=["*"]`) - restrict in production
⚠️ **Authentication**: No user authentication - add auth layer for multi-user
⚠️ **Rate limiting**: No rate limiting - add to prevent abuse
⚠️ **Input sanitization**: Add content filtering for malicious inputs
⚠️ **API key rotation**: Implement key rotation strategy
⚠️ **Logging**: Add comprehensive logging for debugging and monitoring

---

## 📚 Key Learnings

### RAG Pattern
This system implements the **Tool-Use RAG Pattern**:
1. Claude decides when to search (not every query needs it)
2. Semantic search retrieves relevant context
3. Claude synthesizes context into natural answers
4. Sources are tracked for transparency

### Benefits
- **Accuracy**: Answers grounded in actual course content
- **Context-Aware**: Conversation history enables follow-up questions
- **Flexible**: Claude decides when search is needed
- **Transparent**: Sources shown to user for verification
- **Scalable**: Vector search handles large document collections

### Trade-offs
- **Latency**: Two Claude API calls add 3-5 seconds
- **Cost**: Each query costs 2x API calls
- **Complexity**: More moving parts vs simple prompt + context
- **Dependencies**: Requires vector DB, embeddings, tool system

---

## 🚀 Next Steps

To understand more about specific components:
- **Document Processing**: See [backend/document_processor.py](backend/document_processor.py)
- **Vector Storage**: See [backend/vector_store.py](backend/vector_store.py)
- **Session Management**: See [backend/session_manager.py](backend/session_manager.py)
- **Data Models**: See [backend/models.py](backend/models.py)
- **Configuration**: See [backend/config.py](backend/config.py)
