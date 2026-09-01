1. Introduction
1.1 Purpose
This document specifies the software requirements for the King Saud University (KSU) LMS Support Chatbot. It provides developers, project managers, and stakeholders with a detailed blueprint of the system's architecture, features, and constraints.

1.2 Scope
The system is a web-based, AI-driven support chatbot designed for KSU students and faculty using Blackboard. It utilizes a Retrieval-Augmented Generation (RAG) architecture to answer LMS-related queries based on official documentation. If the AI cannot resolve the query, the system seamlessly escalates the session to a human support agent. The solution will replace the legacy system, explicitly resolving historical issues with empty message submissions, lack of presence indicators, and outdated UI layouts.

1.3 Definitions and Acronyms
LMS: Learning Management System (specifically, KSU's Blackboard).


RAG: Retrieval-Augmented Generation, combining vector search with LLM generation.


LLM: Large Language Model (powered locally via Ollama).


Handoff: The process of transferring an active chat from the AI to a human agent.


1.4 Overview
The remaining sections define the product's overarching perspective, specific functional and non-functional requirements, integration interfaces, and underlying system assumptions.

2. Overall Description
2.1 Product Perspective
The system operates as an independent web application accessible via its own dedicated URL, while also supporting seamless iframe embedding within the Blackboard LMS via a ?embed=true query parameter. It is a multi-tier application utilizing a React frontend and a FastAPI (Python) backend.

2.2 Product Functions
Automated, contextual question answering via a RAG pipeline.


Live escalation routing to human agents.


Dedicated management dashboard for support agents.


Real-time chat presence and validation.


Bilingual localization (Arabic/English).


2.3 User Classes
End Users (Students/Faculty): Authenticate using their Name and KSU University ID to seek LMS support.


Support Agents: University IT staff who monitor escalated chats, respond to users, and manage session statuses.


2.4 General Constraints
The system must run AI inference entirely on-premises using free, local models (Ollama) to comply with university data privacy policies.

3. Functional Requirements
FR-01 (Authentication): The system shall require end-users to input their Name and KSU University ID before initiating a chat session.


FR-02 (AI Query Resolution): The system shall query a ChromaDB vector store containing Blackboard documentation and generate an answer using Ollama before prompting human intervention.


FR-03 (Agent Handoff): The system shall provide a visible "Speak to a Human" option. Upon triggering, the system must pause AI responses and route the chat history to the agent dashboard.


FR-04 (Agent Dashboard): Support agents shall have a secure dashboard to view a queue of escalated chats, claim active sessions, and review prior AI-user conversation context.


FR-05 (Input Validation): The frontend shall disable the send button and reject API submissions for empty or whitespace-only messages.


FR-06 (Presence Indicators): The system shall display real-time "AI is thinking..." or "Agent is typing..." indicators during asynchronous response generation or live agent input.


FR-07 (Contextual Embedding): When loaded with the ?embed=true URL parameter, the React frontend shall hide standalone headers/footers to optimize the iframe layout for Blackboard.


4. Non-Functional Requirements
4.1 Performance
The RAG pipeline and FastAPI backend must return the initial AI response chunk within 3.0 seconds of the user's submission.


4.2 Security
All backend API endpoints shall validate origin headers to prevent unauthorized cross-site requests.


Chat logs stored in PostgreSQL must securely isolate user sessions by KSU ID.


4.3 Usability & UI
The user interface must utilize a modern, responsive chat overlay, replacing the legacy full-page design.


The system must meet WCAG 2.1 AA accessibility standards for screen readers and keyboard navigation.


4.4 Bilingual Support
The frontend must support instant toggling between Arabic (RTL) and English (LTR) interfaces without requiring a page reload.


The RAG knowledge base and LLM prompts must process and respond accurately in the user's detected or selected language.


5. External Interface Requirements
5.1 User Interfaces
End-User UI: A React-based chat widget embedded via iframe or accessed standalone.


Agent UI: A React-based web dashboard displaying queued chats, active sessions, and historical transcripts.


5.2 Software Interfaces
Database Engine: PostgreSQL for relational data (users, chat sessions, message logs, agent states).


Vector Store: ChromaDB for storing embedded document chunks.


LLM Engine: Ollama API for generating textual responses locally.


Backend Framework: Python FastAPI serving RESTful endpoints and WebSockets.


5.3 Communication Interfaces
The application shall use HTTPS for all client-server communication.


Real-time events (agent presence, live chat routing) shall be handled via WebSockets natively supported by FastAPI.


6. System Constraints and Assumptions
Assumption: The university will provide adequate bare-metal or GPU-accelerated server infrastructure to run the Ollama LLM with acceptable inference latency.


Assumption: Administrators will periodically manually update the ChromaDB knowledge base as Blackboard features change.


Constraint: The chatbot is strictly limited to LMS support; it is not integrated with KSU's student information system (SIS) for academic advising or grades.

