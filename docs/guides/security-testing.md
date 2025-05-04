# TechSaaS Security Testing Framework

![TechSaaS Logo](../../web-interface/static/images/techsaas-logo.png)

## Overview

This guide explains the TechSaaS automated security testing framework, which helps identify and prevent security vulnerabilities in the platform. Our security testing suite is designed to run both manually during development and automatically in our CI/CD pipeline.

---

## 🚀 Getting Started (Beginner-Friendly)

### What is Security Testing?

Security testing helps us find weaknesses in our application that hackers might exploit. By running these tests regularly, we can identify and fix problems before they become real security issues.

### Running Your First Security Test

If you're new to security testing, follow these simple steps:

1. **Make sure you have the platform running locally:**

```bash
# Start the TechSaaS platform
python start.py
```

2. **In a new terminal, run the security test suite:**

```bash
cd ai-service/tests
python security_test_suite.py --all --verbose
```

3. **Review the results:**
   - A test report will be generated in the current directory
   - Look for any failing tests, which indicate potential security issues
   - The report includes clear explanations of each issue found

### Visual Guide

Here's what the process looks like:

1. Start your local server
2. Run the security tests
3. Review the HTML report that's generated
4. Fix any issues found in the report

---

## 💻 Quick Reference for Experienced Developers

### One-Liner Commands

```bash
# Run all security tests with HTML report
python ai-service/tests/security_test_suite.py --all --report=html

# Run just authentication tests
python ai-service/tests/security_test_suite.py --auth

# Run injection vulnerability tests
python ai-service/tests/security_test_suite.py --injection

# Run in CI mode with JUnit output
python ai-service/tests/security_test_suite.py --all --report=junit --ci

# Run individual test modules
python -m unittest ai-service/tests/security/test_authentication.py
python -m unittest ai-service/tests/security/test_csrf.py
```

### Adding Tests for New Features

When adding a new API endpoint or feature, implement corresponding security tests:

```python
def test_new_feature_security(self):
    """Test security of the new feature"""
    # Setup
    headers = self.headers.copy()
    headers['Authorization'] = f"Bearer {self.valid_token}"
    
    # Test authorization
    response = requests.get(f"{self.base_url}/api/v1/new-feature", headers=headers)
    self.assertEqual(response.status_code, 200)
    
    # Test without auth
    response = requests.get(f"{self.base_url}/api/v1/new-feature")
    self.assertNotEqual(response.status_code, 200)
```

### Common Security Patterns

```python
# Verify CSRF protection
csrf_token = self._get_csrf_token()
headers = {'X-CSRF-TOKEN': csrf_token}
response = session.post(url, headers=headers, json=data)

# Test for XSS vulnerabilities
payload = "<script>alert('XSS')</script>"
response = requests.post(url, json={"name": payload})
self.assertNotIn(payload, response.text)  # Should be encoded/escaped

# Test rate limiting
responses = [requests.get(url) for _ in range(30)]
self.assertTrue(any(r.status_code == 429 for r in responses))
```

---

## 📚 Professional Security Testing Documentation

### Architecture

The TechSaaS Security Testing Framework consists of:

1. **Core Test Runner** (`security_test_suite.py`) - Orchestrates the execution of all security tests and generates reports
2. **Test Modules** - Specialized test classes for different security aspects:
   - Authentication (`test_authentication.py`)
   - Authorization (`test_authorization.py`)
   - Injection attacks (`test_injection.py`)
   - XSS protection (`test_xss.py`)
   - CSRF protection (`test_csrf.py`)
   - Security headers (`test_headers.py`)
   - Rate limiting (`test_rate_limiting.py`)
3. **CI/CD Integration** - GitHub Actions workflow that runs security tests on each PR and scheduled basis
4. **Reporting System** - Generates HTML, JSON, or JUnit-formatted reports

### Comprehensive Test Coverage

| Security Category | Tests Included | Standards |
|-------------------|----------------|-----------|
| Authentication | Token verification, brute force protection, session management | OWASP ASVS V2, V3 |
| Authorization | RBAC, privilege escalation, IDOR | OWASP ASVS V4 |
| Injection | SQL, NoSQL, LDAP, OS command, template | OWASP Top 10 A03 |
| XSS | Reflected, stored, DOM-based | OWASP Top 10 A07 |
| CSRF | Token validation, Same-Origin enforcement | OWASP Top 10 A05 |
| Headers | CSP, X-Content-Type-Options, X-Frame-Options, HSTS | OWASP ASVS V14 |
| Rate Limiting | API, auth, bypass prevention | OWASP API Security Top 10 |

### CI/CD Integration

The security tests are integrated into our CI/CD pipeline through GitHub Actions, with the workflow defined in `.github/workflows/security-tests.yml`. This ensures:

1. Automated security testing on each PR and push to main branches
2. Weekly scheduled scans to catch security regressions
3. Dependency vulnerability scanning via OWASP Dependency Check
4. Security reports uploaded as artifacts for review
5. Notifications on security test failures

### Custom Test Development

When developing new security tests, follow these best practices:

1. **Inherit from unittest.TestCase**:
   ```python
   class NewSecurityTest(unittest.TestCase):
       # Test cases here
   ```

2. **Include clear documentation** in docstrings explaining:
   - The vulnerability being tested
   - The expected secure behavior
   - References to standards (e.g., OWASP)

3. **Implement setUp and tearDown methods** for test environment preparation:
   ```python
   def setUp(self):
       # Setup test environment
       
   def tearDown(self):
       # Clean up after tests
   ```

4. **Use descriptive test names** that explain the security concern:
   ```python
   def test_admin_endpoint_rejects_unauthorized_access(self):
       # Test implementation
   ```

### Best Practices for Fixing Security Issues

When security tests fail, follow this systematic approach:

1. **Understand the vulnerability** by reading the test documentation
2. **Locate the affected code** in the relevant module
3. **Apply the appropriate security control**:
   - Input validation/sanitization for injection/XSS
   - Proper authorization checks for access control
   - CSRF tokens for state-changing operations
   - Security headers for browser protections
4. **Re-run the specific test** to verify the fix
5. **Run the full security suite** to ensure no regressions
6. **Document the fix** in your commit message with references to security standards

### Maintaining Security Tests

To keep security tests effective:

1. **Update tests when adding new features** or changing existing ones
2. **Review security tests quarterly** against the latest OWASP standards
3. **Add tests for any new vulnerability classifications** that emerge
4. **Monitor test performance** to ensure tests aren't becoming false positive sources

---

## Advanced Topics

### Custom Security Test Reporters

The security test suite supports custom reporters through the `--report` parameter:

- `text`: Simple text output (default)
- `json`: JSON-formatted report for programmatic processing
- `html`: Interactive HTML report with vulnerability details
- `junit`: XML format for CI/CD integration

### Integrating with External Security Tools

The security test framework can be extended to integrate with external tools:

```python
def test_zap_scan_results(self):
    """Test that ZAP scan doesn't find vulnerabilities"""
    # Run ZAP scan and parse results
    results = self._run_zap_scan()
    
    # Check if there are high-severity findings
    high_severity_findings = [f for f in results if f['severity'] == 'high']
    self.assertEqual(len(high_severity_findings), 0, 
                   f"ZAP found {len(high_severity_findings)} high-severity issues")
```

### Custom Vulnerability Detection

You can extend the framework to detect application-specific vulnerabilities:

```python
def test_api_key_exposure(self):
    """Test that API keys are not exposed in responses"""
    # Setup with actual API key in the request
    headers = self.headers.copy()
    headers['X-API-Key'] = 'test-api-key-123'
    
    # Make requests to various endpoints
    for endpoint in self.endpoints:
        response = requests.get(endpoint, headers=headers)
        
        # Check that API key is not reflected in response
        self.assertNotIn('test-api-key-123', response.text)
```

---

## API Reference

### `security_test_suite.py`

The main test runner with the following command-line options:

| Option | Description |
|--------|-------------|
| `--all` | Run all security tests |
| `--auth` | Run authentication security tests |
| `--injection` | Run injection attack tests |
| `--xss` | Run XSS attack tests |
| `--csrf` | Run CSRF protection tests |
| `--headers` | Run security headers tests |
| `--session` | Run session security tests |
| `--rate-limit` | Run rate limiting tests |
| `--ci` | Run in CI mode (outputs in JUnit format) |
| `--report=FORMAT` | Output format (text, json, html, junit) |
| `--verbose` | Show verbose output |

### Contact

For questions about the security testing framework, contact the TechSaaS Security Team at security@techsaas.tech.

---

© 2025 TechSaaS. All rights reserved.
