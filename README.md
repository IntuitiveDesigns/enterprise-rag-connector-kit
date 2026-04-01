[![Architecture by Steven Lopez](https://img.shields.io/badge/Architecture%20by-Steven%20Lopez-0077B5?style=for-the-badge&logo=linkedin&logoColor=white)](https://www.linkedin.com/in/steve-lopez-b9941/)
[![GitHub stars](https://img.shields.io/github/stars/IntuitiveDesigns/enterprise-rag-connector-kit?style=for-the-badge)](https://github.com/IntuitiveDesigns/enterprise-rag-connector-kit/stargazers)
[![License](https://img.shields.io/github/license/IntuitiveDesigns/enterprise-rag-connector-kit?style=for-the-badge)](LICENSE)

---

# Enterprise RAG Connector Kit

A modular Python framework for ingesting enterprise content, validating and indexing documents, retrieving grounded context, and exposing a local MCP-compatible chatbot workflow.

The current implementation includes:
- composable source adapters
- batching, validation, retry, and structured logging
- a retrieval + grounded-answer workflow
- an MCP tool for local client integration
- test coverage for core indexing and retrieval paths

## Overview

This project is structured as a reusable connector and retrieval framework rather than a one-off script. It is designed to support repeated onboarding scenarios where content sources, retrieval workflows, and client integrations may evolve over time.

At a high level, the project supports:
- content ingestion from local JSON or REST-based sources
- document validation and batch-oriented indexing
- retrieval of relevant content for a user question
- grounded answer generation with source attribution
- local MCP exposure for compatible developer tools

## Architecture

```text
Source Data
   ↓
Adapter
   ↓
Validator
   ↓
Indexing Engine
   ↓
Provider Indexing API

User Question
   ↓
RAG Service
   ↓
Search API → Retrieve Documents
   ↓
Chat API → Generate Answer
   ↓
Return Answer + Sources

---

## Quick Start

```bash
# Activate the cirtual environment
.\.venv\Scripts\Activate.ps1

# Sanity-check the codebase
pytest
ruff check .

# Indexing flow
python .\main.py

# Search API verification script
python .\verify_indexing.py

# Chatbot from CLI
python .\ask_chatbot.py "Which documents discuss observability?" 5

# MCP server
python -m glean_indexing_connector.mcp.server

# MCP Tool (Web Interface)
mcp dev src\glean_indexing_connector\mcp\server.py
or
python -m mcp dev src\glean_indexing_connector\mcp\server.py

```
