# OpsLens

Agentic Cloud & Software Supply Chain Intelligence on AWS.

OpsLens is an open-source software supply chain intelligence platform designed to answer:

> Given the software I actually use, which vulnerabilities represent material risk, why, and what should I do about them?

## Status

Early implementation — AWS foundation.

## Core principles

- Deterministic evidence and correlation first; generative reasoning second.
- Not every question is a RAG problem.
- Never execute third-party repository code.
- Repository risk and runtime exposure are separate concepts.
- IAM least privilege, cost controls, and observability are architectural requirements.

## Infrastructure

The initial deployment uses a single real environment:

- Environment: `dev`
- Primary workload Region: `us-east-1`
- Infrastructure as Code: Terraform

Implementation is intentionally incremental.
