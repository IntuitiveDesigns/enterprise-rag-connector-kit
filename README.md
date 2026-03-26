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