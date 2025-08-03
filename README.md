# Resume Builder Service

A comprehensive microservice for creating, managing, and optimizing professional resumes with advanced ATS (Applicant Tracking System) analysis as part of the JobReadyNow platform.

## 🚀 Features

### Core Resume Management
- **CRUD Operations**: Create, read, update, and delete resumes
- **Template System**: Multiple professional resume templates
- **PDF Export**: Generate PDF versions of resumes
- **Resume Validation**: Comprehensive content validation and scoring
- **Version Control**: Track resume changes and versions

### 🎯 ATS Analysis & Optimization (NEW!)
- **ATS Score Analysis**: Comprehensive scoring with 6 key metrics
- **Keyword Optimization**: Industry-specific keyword analysis and suggestions
- **Job Matching**: Compare resume against specific job descriptions
- **Industry Benchmarking**: Compare against industry standards
- **Optimization Suggestions**: Specific before/after text improvements
- **Score History Tracking**: Monitor improvement over time
- **Bulk Analysis**: Analyze multiple resumes simultaneously

### Additional Features
- **Authentication**: JWT-based authentication integration with main API
- **Rate Limiting**: Built-in API protection
- **Health Checks**: Comprehensive health monitoring

## 📊 ATS Analysis Capabilities

### Scoring Metrics
1. **Overall ATS Score** (0-100): Comprehensive compatibility score
2. **Formatting Score**: Structure and ATS parsing compatibility
3. **Keyword Score**: Relevance and density of industry keywords
4. **Content Structure Score**: Quality and organization of content
5. **Readability Score**: Clarity and professional language
6. **Job Match Percentage**: Alignment with specific job requirements

### Analysis Features
- **Industry-Specific Analysis**: Tailored scoring for Technology, Healthcare, Finance, etc.
- **Skill Gap Identification**: Missing skills compared to job requirements
- **Keyword Density Analysis**: Optimal keyword usage recommendations
- **Trend Tracking**: Historical score improvements over time
- **Benchmarking**: Compare against industry averages by role level

## 🛠 Tech Stack

- **Framework**: FastAPI 0.104.1
- **Database**: PostgreSQL with SQLAlchemy 2.0
- **Authentication**: JWT integration with main JobReadyNow API
- **PDF Generation**: ReportLab
- **ATS Analysis**: Custom keyword matching and scoring algorithms
- **Caching**: Redis
- **Testing**: Pytest
- **Container**: Docker & Docker Compose

## 📚 API Documentation

### Core Resume Endpoints
- `POST /api/v1/resumes/` - Create a new resume
- `GET /api/v1/resumes/` - List user's resumes
- `GET /api/v1/resumes/{id}` - Get specific resume
- `PUT /api/v1/resumes/{id}` - Update resume
- `DELETE /api/v1/resumes/{id}` - Delete resume
- `POST /api/v1/resumes/{id}/duplicate` - Duplicate resume
- `POST /api/v1/resumes/{id}/validate` - Validate resume
- `GET /api/v1/resumes/{id}/preview` - Get HTML preview
- `POST /api/v1/resumes/{id}/export` - Export to PDF

### 🎯 ATS Analysis Endpoints (NEW!)
- `POST /api/v1/ats/{resume_id}/analyze` - Comprehensive ATS analysis
- `GET /api/v1/ats/{resume_id}/score-history` - Historical ATS scores
- `POST /api/v1/ats/{resume_id}/compare-jobs` - Compare against multiple jobs
- `POST /api/v1/ats/{resume_id}/optimization-suggestions` - Get specific improvements
- `GET /api/v1/ats/{resume_id}/ats-report` - Comprehensive analysis report
- `POST /api/v1/ats/bulk-analyze` - Analyze multiple resumes
- `GET /api/v1/ats/benchmarks` - Industry benchmarks

### Template & Export Endpoints
- `GET /api/v1/templates/` - List available templates
- `GET /api/v1/templates/{id}` - Get template details
- `GET /api/v1/export/formats` - Supported export formats
- `GET /api/v1/export/{export_id}/download` - Download exported file

## 🎯 ATS Analysis Usage Examples

### Basic ATS Analysis
```bash
curl -X POST "http://localhost:8001/api/v1/ats/{resume_id}/analyze" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "job_description": "We are seeking a Senior Software Engineer with 5+ years of experience in Python, React, and cloud technologies. Must have experience with AWS, Docker, and agile methodologies.",
    "target_industry": "technology",
    "include_skill_gaps": true,
    "include_recommendations": true
  }'
```

### Response Example
```json
{
  "overall_ats_score": 84,
  "formatting_score": 92,
  "keyword_score": 78,
  "content_structure_score": 86,
  "readability_score": 89,
  "job_match_percentage": 73.5,
  "keyword_analysis": {
    "score": 78,
    "total_keywords": 45,
    "matched_keywords": ["python", "react", "aws", "docker"],
    "missing_keywords": ["agile", "cloud", "senior"],
    "keyword_density": 6.2
  },
  "skill_gaps": {
    "skill_match_percentage": 70.0,
    "critical_missing": ["AWS certification", "Agile experience"],
    "important_missing": ["Docker", "Kubernetes"],
    "nice_to_have_missing": ["GraphQL", "TypeScript"]
  },
  "recommendations": [
    {
      "category": "keywords",
      "priority": "high", 
      "title": "Add Missing Technical Keywords",
      "description": "Your resume is missing key technical terms from the job description",
      "impact": "Increases ATS keyword matching by 15-20%",
      "action_items": [
        "Add 'Agile methodologies' to your work experience",
        "Include 'Cloud technologies' in your skills section",
        "Mention 'Senior-level' responsibilities in job descriptions"
      ]
    }
  ],
  "industry_insights": {
    "industry": "technology",
    "benchmarks": {
      "average_ats_score": 75,
      "recommended_length": "600-800 words"
    },
    "trends": ["AI/ML", "Cloud Computing", "DevOps"]
  }
}
```

### Compare Against Multiple Jobs
```bash
curl -X POST "http://localhost:8001/api/v1/ats/{resume_id}/compare-jobs" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "job_descriptions": [
      "Frontend Developer position requiring React, TypeScript, and modern CSS",
      "Full Stack Engineer role with Node.js, Python, and database experience",
      "DevOps Engineer position focusing on AWS, Docker, and CI/CD"
    ],
    "job_titles": ["Frontend Dev", "Full Stack", "DevOps"]
  }'
```

### Get Optimization Suggestions
```bash
curl -X POST "http://localhost:8001/api/v1/ats/{resume_id}/optimization-suggestions" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "job_description": "Senior Software Engineer position...",
    "target_industry": "technology",
    "max_suggestions": 5
  }'
```

## 🏗 Resume Content Schema

### Enhanced Resume Structure
```json
{
  "personal_info": {
    "first_name": "string",
    "last_name": "string", 
    "email": "string",
    "phone": "string",
    "address": "string",
    "linkedin_url": "string",
    "portfolio_url": "string",
    "github_url": "string"
  },
  "professional_summary": "string (optimized for ATS keywords)",
  "work_experience": [
    {
      "job_title": "string",
      "company": "string",
      "start_date": "YYYY-MM",
      "end_date": "YYYY-MM",
      "location": "string",
      "responsibilities": [
        "Action verb + quantified achievement + relevant keywords"
      ]
    }
  ],
  "education": [...],
  "skills": {
    "technical": ["keyword-optimized skills"],
    "soft": ["ATS-friendly soft skills"],
    "languages": ["programming languages"],
    "tools": ["industry-standard tools"]
  },
  "certifications": [...],
  "projects": [...],
  "languages": [...]
}
```
```

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL connection string | `postgresql://postgres:password@localhost:5432/resume_builder` |
| `JWT_SECRET_KEY` | Secret key for JWT validation | Required |
| `MAIN_API_URL` | Main JobReadyNow API URL | `http://localhost:8000/api/v1` |
| `REDIS_URL` | Redis connection string | `redis://localhost:6379` |
| `ENVIRONMENT` | Environment (development/production) | `development` |
| `DEBUG` | Enable debug mode | `true` |
| `LOG_LEVEL` | Logging level | `INFO` |
| `ALLOWED_ORIGINS` | CORS allowed origins | `["http://localhost:3000"]` |

### Sample .env File
```env
DATABASE_URL=postgresql://postgres:password@localhost:5432/resume_builder
JWT_SECRET_KEY=your-super-secret-jwt-key-here
MAIN_API_URL=http://localhost:8000/api/v1
REDIS_URL=redis://localhost:6379
ENVIRONMENT=development
DEBUG=true
LOG_LEVEL=INFO
ALLOWED_ORIGINS=["http://localhost:3000","http://localhost:8000"]
```

## Testing

### Run Tests
```bash
# Install test dependencies
pip install pytest pytest-asyncio httpx

# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific test file
pytest tests/test_api/test_resumes.py

# Run with verbose output
pytest -v
```

### Test Structure
```
tests/
├── conftest.py           # Test configuration and fixtures
├── test_api/
│   ├── test_resumes.py   # Resume API tests
│   ├── test_templates.py # Template API tests
│   └── test_export.py    # Export API tests
├── test_services/
│   ├── test_resume_service.py
│   ├── test_export_service.py
│   └── test_validation_service.py
└── test_utils/
    ├── test_validators.py
    └── test_pdf_generator.py
```

## Database Migrations

### Create Migration
```bash
alembic revision --autogenerate -m "Description of changes"
```

### Apply Migrations
```bash
alembic upgrade head
```

### Rollback Migration
```bash
alembic downgrade -1
```

## Monitoring and Health Checks

### Health Endpoints
- `GET /health` - Basic health check
- `GET /health/detailed` - Detailed health with dependency checks

### Logging
The service uses structured logging with the following levels:
- **ERROR**: Application errors and exceptions
- **WARNING**: Validation failures and business logic warnings
- **INFO**: Request/response logging and business events
- **DEBUG**: Detailed debugging information

### Metrics
Monitor these key metrics in production:
- Request/response times
- Error rates
- PDF generation times
- Database query performance
- Cache hit rates

## Security

### Authentication
- JWT tokens validated with main JobReadyNow API
- All resume operations require valid authentication
- User ownership verification for all operations

### Data Protection
- Input validation on all endpoints
- SQL injection prevention via SQLAlchemy ORM
- XSS protection through input sanitization
- Rate limiting to prevent abuse

### CORS Configuration
Configure allowed origins in production:
```python
ALLOWED_ORIGINS=["https://jobreadynow.com","https://app.jobreadynow.com"]
```

## Performance Optimization

### Database
- Indexes on frequently queried fields
- Connection pooling with SQLAlchemy
- Efficient pagination with offset/limit

### Caching
- Redis for session and template caching
- Application-level caching for frequently accessed data

### PDF Generation
- Optimized ReportLab templates
- Async processing for large documents
- File cleanup after export

## Deployment

### Production Deployment
1. **Set environment variables**
   ```bash
   export ENVIRONMENT=production
   export DEBUG=false
   export DATABASE_URL=your_production_db_url
   export JWT_SECRET_KEY=your_production_secret
   ```

2. **Run database migrations**
   ```bash
   alembic upgrade head
   ```

3. **Start with Gunicorn**
   ```bash
   gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker -b 0.0.0.0:8001
   ```

### Docker Production
```yaml
# docker-compose.prod.yml
services:
  resume-service:
    image: your-registry/resume-builder:latest
    environment:
      - ENVIRONMENT=production
      - DEBUG=false
    restart: always
```

### Scaling Considerations
- **Horizontal Scaling**: Multiple container instances behind load balancer
- **Database**: Read replicas for high-read workloads
- **File Storage**: Move to cloud storage (S3, GCS) for generated PDFs
- **Caching**: Redis cluster for high availability

## API Integration

### Main JobReadyNow API Integration
The service integrates with the main API for:
- User authentication and profile data
- File storage coordination
- Notification sending

### Example Integration Code
```python
# Verify user with main API
async with httpx.AsyncClient() as client:
    response = await client.get(
        f"{MAIN_API_URL}/auth/me",
        headers={"Authorization": f"Bearer {token}"}
    )
    user_data = response.json()
```

## Contributing

### Development Setup
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Run the test suite
6. Submit a pull request

### Code Style
- Follow PEP 8 standards
- Use type hints
- Write docstrings for functions and classes
- Keep functions focused and small

### Commit Guidelines
```
feat: add new resume template
fix: resolve PDF generation issue
docs: update API documentation
test: add validation service tests
```

## Troubleshooting

### Common Issues

**Database Connection Errors**
```bash
# Check database is running
docker-compose ps postgres

# Check database connectivity
psql -h localhost -U postgres -d resume_builder
```

**PDF Generation Fails**
- Check ReportLab installation
- Verify template paths exist
- Check font availability

**Authentication Issues**
- Verify JWT_SECRET_KEY matches main API
- Check token expiration
- Validate main API connectivity

**Performance Issues**
- Check database query performance
- Monitor Redis cache hit rates
- Review PDF generation times

### Logs and Debugging
```bash
# View application logs
docker-compose logs resume-service

# Follow logs in real-time
docker-compose logs -f resume-service

# Debug mode
export DEBUG=true
export LOG_LEVEL=DEBUG
```

## License

This project is part of the JobReadyNow platform. See LICENSE file for details.

## Support

For technical support and questions:
- Create an issue in the repository
- Contact the development team
- Check the API documentation at `/docs`

---

**Version**: 1.0.0  
**Last Updated**: 2024-01-15