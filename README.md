# TechSaaS Platform

A comprehensive web platform that combines video scraping capabilities using Hitomi-Downloader integration, AI-powered analysis with LangChain and Ollama, and a secure microservices architecture.

![TechSaaS Logo](https://placeholder-for-techsaas-logo.com)

## Project Overview

The TechSaaS platform is a production-ready solution designed to demonstrate advanced web technologies and provide a learning resource for developers at all skill levels. The system integrates:

- Advanced video scraping with Hitomi-Downloader
- AI analysis using LangChain with Ollama integration (In Progress)
- Web browser interface with search capabilities
- Comprehensive security layer and API gateway
- Microservices architecture with Flask

## Current Development Status (May 2, 2025)

- **Video Scraper**: Core functionality stable and working
- **LangChain & Ollama Integration**: Detailed subtasks created, implementation beginning
- **Task Management**: Using Task Master for organized development workflow
- **UI/UX**: Core interface is responsive and user-friendly 

## Repository Structure

```
techsaas-platform/
├── api-gateway/                   # API Gateway service
├── video-scraper/                 # Video Scraper service with Hitomi
├── web-interface/                 # Web Browser Interface
├── ai-service/                    # LangChain AI service (Task 5 - In Progress)
├── security/                      # Security components
├── docs/                          # Documentation
└── [other project files]
```

## Documentation

This project is extensively documented to serve as both a functional application and a learning resource:

- [Project Roadmap](video-scraper/ROADMAP.md) - Comprehensive overview and timeline
- [Developer Journal](docs/journal/DEVELOPER_JOURNAL.md) - Step-by-step development log
- [Git Setup Guide](docs/GIT_SETUP.md) - Git/GitHub repository configuration
- [API Documentation](docs/api/) - API endpoint references
- [Architecture Guide](docs/architecture/) - System design and patterns
- [Beginner Tutorials](docs/beginners/) - Step-by-step guides for new developers

## Development Process

This project follows a structured task-driven development methodology using the Task Master system. To contribute or understand the implementation process:

1. Review the [Project Roadmap](video-scraper/ROADMAP.md)
2. Check current tasks with `task-master list`
3. Examine the [Developer Journal](docs/journal/DEVELOPER_JOURNAL.md) for implementation details
4. Follow the [Git Setup Guide](docs/GIT_SETUP.md) for repository management

## Getting Started

### Prerequisites

- Python 3.9+
- Node.js 16+
- Git

### Installation

```bash
# Clone the repository
git clone https://github.com/525277x/techsaas-platform.git
cd techsaas-platform

# Set up virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set up Node.js dependencies
cd web-interface
npm install
cd ..

# Initialize Task Master (optional for development)
task-master init
```

### Running the Services

```bash
# Start API Gateway
cd api-gateway
python app.py
# Service will be available at http://localhost:5000

# Start Video Scraper Service
cd video-scraper
python app.py
# Service will be available at http://localhost:5500

# Start Web Interface
cd web-interface
python app.py
# Interface will be available at http://localhost:5252
```

## Contributing

We welcome contributions to this project! Please follow our [Contribution Guidelines](docs/CONTRIBUTING.md) and review the [Git Setup Guide](docs/GIT_SETUP.md) for repository management practices.

## Security

This project implements and demonstrates comprehensive security practices. See [Security Documentation](docs/security/) for implementation details. Please report any security concerns following our [Security Policy](SECURITY.md).

## License

This project is released under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- [Hitomi-Downloader](https://github.com/KurtBestor/Hitomi-Downloader) for video scraping capabilities
- [LangChain](https://github.com/langchain-ai/langchain) for AI framework
- [Ollama](https://github.com/ollama/ollama) for local language model runtime
- [Flask](https://flask.palletsprojects.com/) for API and web services
- [Task Master](https://github.com/eyaltoledano/claude-task-master) for project management

## Contact

- Twitter: [@525277x](https://twitter.com/525277x)
- GitHub: [525277x](https://github.com/525277x)
- Website: [TechSaaS.Tech](https://techsaas.tech)

---

 2025 5252LLC | TechSaaS.Tech
