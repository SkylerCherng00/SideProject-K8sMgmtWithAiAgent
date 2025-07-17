# LLM Management Agent

[![.NET 9](https://img.shields.io/badge/.NET-9-512BD4)](https://dotnet.microsoft.com/)
[![ASP.NET Core](https://img.shields.io/badge/ASP.NET%20Core-9.0-blue)](https://docs.microsoft.com/en-us/aspnet/core/)
[![Python 3.12](https://img.shields.io/badge/Python-3.12-blue)](https://www.python.org/downloads/release/python-3120/)
[![Kubernetes 1.32](https://img.shields.io/badge/Kubernetes-v1.32-green)](https://kubernetes.io/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## Overview

LLM Management Agent is a web application built with ASP.NET Core that combines AI chat functionality with Kubernetes cluster monitoring. It provides an intuitive interface for interacting with AI models and managing Kubernetes resources from a single dashboard.

Screenshot

## Features

- **AI Chat Assistant**: Interact with LLM models through a conversational interface
- **Kubernetes Monitoring**:
  - Real-time pod metrics visualization
  - Resource utilization tracking
  - Pod logs viewing and searching
  - Cluster state analysis
- **Responsive Design**: Works on desktop and mobile devices
- **Markdown Support**: Rich formatting for AI responses and analysis reports

##  Getting Started

### Installation

- Current Support deployment is on Docker
- The stops for deployment:
  - cd to the `deployment` directory
  - `docker compose up -d --build`
  - The application will be available at `http://localhost:8081`

##  Architecture

LLMMgmt follows the MVC (Model-View-Controller) architectural pattern:

- **Models**: Data structures for AI chat, Kubernetes metrics, and analysis results
- **Views**: Razor views for rendering UI components
- **Controllers**: Process user actions and API interactions
- **Services**: Handle external API calls and business logic

### Key Components

- llm_mgmt_web: ASP.NET Core MVC application
- llm_client: FastAPI forClient application for AI chat and analysis
- loki: FastAPI for Loki logging service
- prom: FastAPI for Prometheus metrics service

## Technologies

- **Backend**: ASP.NET Core 9.0, C#; Python 3.12 for FastAPI integration
- **Frontend**: HTML5, CSS3, JavaScript, Bootstrap 5
- **Data Visualization**: Chart.js for metrics display
- **Text Processing**: Markdown rendering for AI outputs
- **API Communication**: HttpClient, System.Text.Json

##  Workflow

1. **AI Chat**: 
   - User sends message through the chat interface
   - Message is processed by backend services
   - AI response is displayed with markdown formatting

2. **Kubernetes Monitoring**:
   - Application connects to Kubernetes API
   - Metrics are collected and visualized
   - Users can filter and analyze data
   - Automated analysis provides insights on cluster health

## Screenshots

| AI Chat | Kubernetes Dashboard | Pod Logs |
|---------|---------------------|----------|
| ... |... |... |

## Future Enhancements

- Long-term memory for AI interactions
- User authentication and authorization
- Integration with CI/CD pipelines

## Contact

Project Link: [https://github.com/SkylerCherng00/SideProjectK8sMgmt](https://github.com/SkylerCherng00/SideProjectK8sMgmt)

---

<p align="center">
  Made with using ASP.NET Core and Python for AI integration
</p>