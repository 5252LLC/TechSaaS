# TechSaaS Platform: Git & GitHub Setup Guide

## Repository Setup

### Local Repository
```bash
# Navigate to project directory
cd /home/fiftytwo/Desktop/52\ codes/52TechSaas

# Initialize Git repository if not already done
git init

# Configure user information
git config user.name "525277x"
git config user.email "525277x@gmail.com"
```

### GitHub Repository Setup
1. Create a new repository on GitHub at: https://github.com/525277x/techsaas-platform
2. Configure the repository with the following settings:
   - **Repository name**: techsaas-platform
   - **Description**: A comprehensive platform combining video scraping, AI-powered analysis, and secure web interfaces
   - **Visibility**: Public (or Private based on preference)
   - **Initialize with**: README.md, .gitignore (Python template), LICENSE (MIT)

3. Connect local repository to GitHub:
```bash
git remote add origin https://github.com/525277x/techsaas-platform.git
git branch -M main
git push -u origin main
```

## Repository Structure

The repository follows a microservices-based structure with documentation:

```
techsaas-platform/
├── .github/                       # GitHub-specific files
├── api-gateway/                   # API Gateway service
├── video-scraper/                 # Video Scraper service with Hitomi
├── web-interface/                 # Web Browser Interface
├── ai-service/                    # LangChain AI service
├── security/                      # Security components
├── docs/                          # Documentation
│   ├── api/                       # API documentation
│   ├── tutorials/                 # Step-by-step tutorials
│   ├── architecture/              # Architecture diagrams
│   ├── journal/                   # Development journal
│   ├── beginners/                 # Beginner guides
│   └── patterns/                  # Implementation patterns
├── scripts/                       # Utility scripts
├── tasks/                         # Task Master task definitions
├── .gitignore                     # Git ignore file 
├── LICENSE                        # Project license
├── README.md                      # Project overview
└── requirements.txt               # Python dependencies
```

## Branching Strategy

This project uses a modified GitFlow workflow:

- `main`: Production-ready code. All code here is deployable
- `develop`: Integration branch for completed features
- `feature/*`: Individual feature branches (e.g., `feature/video-scraper`)
- `release/*`: Release preparation branches
- `hotfix/*`: Emergency fixes for production issues

### Branch Commands

```bash
# Create a new feature branch
git checkout -b feature/feature-name develop

# Merge completed feature into develop
git checkout develop
git merge --no-ff feature/feature-name
git push origin develop

# Create a release branch
git checkout -b release/1.0.0 develop

# Merge release into main and develop
git checkout main
git merge --no-ff release/1.0.0
git tag -a v1.0.0 -m "Version 1.0.0"
git push origin main --tags

git checkout develop
git merge --no-ff release/1.0.0
git push origin develop
```

## Commit Guidelines

Follow these guidelines for commit messages:

1. Use the imperative mood ("Add feature" not "Added feature")
2. First line is a summary (max 50 characters)
3. Skip a line after the summary for detailed description
4. Reference issue numbers when relevant: "Fixes #123"

Example:
```
Add video extraction functionality for YouTube

- Implements yt-dlp integration
- Adds metadata extraction
- Creates download queue management
- Adds error handling for region restrictions

Fixes #42
```

## GitHub Issue Integration

Link Task Master tasks to GitHub issues:

1. Create a GitHub issue for each Task Master task
2. Include task ID in issue title: `[Task #3] Create Video Scraper Flask API`
3. Update task files to include GitHub issue number

### Automated Issue Tracking Script

Located in `scripts/update_issues.py`, this script synchronizes Task Master tasks with GitHub issues.

## GitHub Actions Workflows

This repository uses GitHub Actions for CI/CD:

1. **Testing Workflow** (.github/workflows/test.yml):
   - Runs on push to develop and pull requests to main
   - Executes unit and integration tests
   - Checks code style with flake8
   - Reports test coverage

2. **Documentation Workflow** (.github/workflows/documentation.yml):
   - Runs on push to main
   - Generates API documentation
   - Updates GitHub Pages

3. **Deployment Workflow** (.github/workflows/deploy.yml):
   - Runs on release tag creation
   - Deploys to staging/production environments

## Git Hooks

Custom Git hooks enhance workflow:

1. **pre-commit**: Runs code linting and tests
2. **commit-msg**: Validates commit message format
3. **post-commit**: Updates Task Master task status

### Setup Git Hooks
```bash
cp scripts/git-hooks/* .git/hooks/
chmod +x .git/hooks/*
```

## GitHub Project Board

The project uses GitHub Projects for task visualization:

1. **To Do**: Tasks ready to be worked on
2. **In Progress**: Currently being implemented
3. **Review**: Awaiting code review
4. **Done**: Completed tasks

Each card is linked to a GitHub issue and corresponding Task Master task.

## Documentation Updates

When creating or modifying code, update documentation:

1. Update API documentation with any interface changes
2. Modify architecture diagrams when components change
3. Add tutorial sections for new features
4. Keep the developer journal updated with decisions and progress

## Security Considerations

Never commit sensitive information:

1. Use environment variables for API keys and credentials
2. Add sensitive files to .gitignore
3. Use GitHub Secrets for CI/CD variables
4. Scan code for accidental credential exposure before commits

## GitHub Configuration

Recommended repository settings:

1. **Branch Protection**:
   - Require pull request reviews for main and develop
   - Require status checks to pass
   - Restrict who can push to main

2. **Security**:
   - Enable Dependabot alerts
   - Enable code scanning
   - Configure security policy in SECURITY.md
