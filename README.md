# K8s Management with AI Agent

[![.NET 9](https://img.shields.io/badge/.NET-9-512BD4)](https://dotnet.microsoft.com/)
[![ASP.NET Core](https://img.shields.io/badge/ASP.NET%20Core-9.0-blue)](https://docs.microsoft.com/en-us/aspnet/core/)
[![Python 3.12](https://img.shields.io/badge/Python-3.12-blue)](https://www.python.org/downloads/release/python-3120/)
[![LangChain-core 0.3.69](https://img.shields.io/badge/LangChain-0.3.69-blue)](https://python.langchain.com/docs/)
[![Kubernetes 1.32](https://img.shields.io/badge/Kubernetes-v1.32-green)](https://kubernetes.io/)
[![PostgreSQL 14](https://img.shields.io/badge/PostgreSQL-v14)](https://kubernetes.io/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## Overview

K8s Management with AI Agent is a sophisticated web application that seamlessly integrates AI-powered chat functionality with comprehensive Kubernetes cluster monitoring capabilities. Built with ASP.NET Core for the web interface and Python FastAPI for the AI components, this system provides Kubernetes administrators with an intuitive dashboard for both intelligent interaction and operational monitoring of Kubernetes resources.

<img src="https://github.com/SkylerCherng00/SideProjectK8sMgmt/blob/main/systemScreenshots/Frontpage.png?raw=true">

## Key Features

- **AI-Powered Chat Assistant**: 
  - Interactive conversation with Azure OpenAI LLM models
  - Real-time Kubernetes cluster analysis and recommendations
  - Support for troubleshooting and operational queries
  - Markdown-formatted responses for enhanced readability

- **Comprehensive Kubernetes Monitoring**:
  - Real-time pod metrics visualization with dynamic charts
  - Detailed resource utilization tracking across namespaces
  - Advanced pod logs viewing with filtering and search capabilities
  - Automated cluster health analysis and anomaly detection

## Getting Started

### Deployment

The application is containerized and supports deployment via Docker:

1. Navigate to the deployment directory:
   ```bash
   cd deployment
   ```

2. Build and start the containers:
   ```bash
   docker compose up -d --build
   ```

3. Access the application:
   ```
   http://localhost:8081
   ```

> **Important**: Review the **DockerNotes.md** file for critical setup information. The `llm_client` container requires SSH key exchange with the Jump Server for proper functioning of the Kubernetes tools. (Security Issue)

## System Architecture

### Application Architecture

The application follows a clean MVC (Model-View-Controller) architectural pattern enhanced with service layers:

- **Models**: Structured data entities representing AI chat conversations, Kubernetes metrics, and analysis results
- **Views**: Razor-based templates providing responsive user interfaces with real-time data visualization
- **Controllers**: Orchestration layer handling user requests, API coordination, and data flow management
- **Services**: Specialized components managing external API communication, business logic, and data processing

### Infrastructure Components

The system operates across four primary virtual machines:

- **Jump Server**: Hosts Docker services and FastAPI endpoints for metrics queries, logs, and the LLM client
- **Server**: Functions as the Kubernetes control plane managing the cluster
- **Node-0 & Node-1**: Worker nodes executing containerized workloads
- **PLG Stack**: Prometheus, Loki, and Grafana running on the Kubernetes cluster for comprehensive observability

### Microservice Components

The application consists of four interconnected microservices:

1. **llm_mgmt_web**: ASP.NET Core MVC application providing the user interface and dashboard functionality
2. **llm_client**: Python FastAPI service implementing AI chat capabilities with LangChain and Azure OpenAI integration
3. **loki**: FastAPI service for accessing and querying log data from the Loki logging subsystem
4. **prom**: FastAPI service for retrieving metrics from the Prometheus monitoring system

## Technology Stack

- **ASP.NET Core 9.0**: High-performance C# framework for web applications
- **Python 3.12**: Powers the AI components and API integrations
- **FastAPI**: Modern, high-performance Python web framework for microservices
- **Azure OpenAI**: Enterprise-grade LLM capabilities for intelligent assistance
- **LangChain**: Framework for developing applications powered by language models

## System Workflow

### AI Chat Interaction
1. **User Query Submission**: 
   - User submits a natural language question or request via the chat interface
   - Request is sent to the backend services for processing
   - Security validation ensures the request conforms to Kubernetes operational constraints
   - The LLM follows the ReAct prompting and uses tool calling to collect the K8s information

2. **Intelligent Processing**:
   - Azure OpenAI processes the query with system context and safety guardrails
   - LangChain framework orchestrates tool selection for Kubernetes data retrieval
   - Multi-step reasoning generates comprehensive analysis and actionable insights

3. **Response Rendering**:
   - AI-generated response is formatted with Markdown for readability
   - Results are displayed in the UI with proper formatting and syntax highlighting
   - Supporting data visualizations are generated where appropriate

### Kubernetes Monitoring Flow
1. **Data Collection**: 
   - System connects to Kubernetes API via secure endpoints in Jump Server
   - Metrics are gathered from Prometheus for resource utilization
   - Log data is collected from Loki for operational insights

2. **Analysis & Processing**:
   - Real-time data processing identifies patterns and anomalies
   - Cross-correlation of metrics, logs, and state information
   - Time-series analysis for trending and forecasting

3. **Visualization & Insights**:
   - Dynamic dashboards display pod health, resource usage, and system state
   - Interactive filtering and search capabilities for targeted analysis
   - AI-powered recommendations highlight potential improvements and issues

## Screenshots

- AI Assistant: `systemScreenshots/AIChat02.png`
  - <img src="https://github.com/SkylerCherng00/SideProjectK8sMgmt/blob/main/systemScreenshots/AIChat02.png?raw=true">
- AI Analysis: `systemScreenshots/Analyze01.png`
  - <img src="https://github.com/SkylerCherng00/SideProjectK8sMgmt/blob/main/systemScreenshots/Analyze01.png?raw=true">
- Pods metrics monitoring: `systemScreenshots/Metrics01.png`
  - <img src="https://github.com/SkylerCherng00/SideProjectK8sMgmt/blob/main/systemScreenshots/Metrics01.png?raw=true">
- Logs querying: `systemScreenshots/Logs01.png`
  - <img src="https://github.com/SkylerCherng00/SideProjectK8sMgmt/blob/main/systemScreenshots/Logs01.png?raw=true">
- RWD Supported: `systemScreenshots/RWDSupport.png`
  - <img src="https://github.com/SkylerCherng00/SideProjectK8sMgmt/blob/main/systemScreenshots/RWDSupport.png?raw=true">

## Roadmap & Future Enhancements

The project has an active development roadmap with planned enhancements:

- **AI Capabilities**:
  - Persistent memory for contextual AI interactions
  - Advanced anomaly detection for proactive monitoring
  - Expanded knowledge base for specialized Kubernetes patterns

- **Security & Access Control**:
  - Comprehensive user authentication and role-based authorization
  - Enhanced audit logging for compliance and security
  - Fine-grained access controls for multi-tenant environments

- **Integration & Extensions**:
  - CI/CD pipeline integration for deployment insights
  - Extended API ecosystem for third-party tool integration
  - Advanced notification system for alerts and events
  - **Tracing Integration**:
    - Integration with Tempo for distributed tracing of microservices
    - Visualize end-to-end request flows and latency bottlenecks
    - Correlate traces with logs and metrics for comprehensive troubleshooting

## Contact & Contribution

This project is open to collaboration and contributions. For questions, feature requests, or issues, please reach out through the GitHub repository.

Project Repository: [https://github.com/SkylerCherng00/SideProjectK8sMgmt](https://github.com/SkylerCherng00/SideProjectK8sMgmt)

---

<p align="center">
  <strong>K8s Management with AI Agent</strong><br>
  Built with ASP.NET Core and Python, powered by Azure OpenAI
</p>
