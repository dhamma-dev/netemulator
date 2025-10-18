# Contributing to NetEmulator

Thank you for your interest in contributing to NetEmulator!

## Development Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/appneta/netemulator.git
   cd netemulator
   ```

2. **Install dependencies**
   ```bash
   sudo make install
   ```

3. **Activate virtual environment**
   ```bash
   source venv/bin/activate
   ```

## Development Workflow

### Making Changes

1. **Create a feature branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make your changes**
   - Follow PEP 8 style guidelines
   - Add tests for new functionality
   - Update documentation as needed

3. **Format your code**
   ```bash
   make format
   ```

4. **Run tests**
   ```bash
   make test
   ```

5. **Run linters**
   ```bash
   make lint
   ```

### Testing

- Write unit tests in `tests/`
- Use pytest for testing
- Aim for >80% code coverage
- Test both success and failure cases

Example test:
```python
def test_my_feature():
    """Test my new feature."""
    result = my_function()
    assert result == expected_value
```

### Code Style

- Use type hints where possible
- Write docstrings for all public functions/classes
- Follow Google Python Style Guide for docstrings
- Maximum line length: 100 characters

Example:
```python
def process_topology(topology: Topology) -> Dict[str, Any]:
    """
    Process a network topology.
    
    Args:
        topology: Topology object to process
        
    Returns:
        Dictionary with processing results
        
    Raises:
        ValueError: If topology is invalid
    """
    pass
```

### Commit Messages

- Use clear, descriptive commit messages
- Follow conventional commits format:
  - `feat:` for new features
  - `fix:` for bug fixes
  - `docs:` for documentation
  - `test:` for tests
  - `refactor:` for refactoring

Example:
```
feat: add support for VXLAN encapsulation

- Implement VXLAN tunnel creation
- Add configuration options for VNI
- Update documentation
```

## Pull Request Process

1. **Update documentation**
   - Update README.md if needed
   - Add docstrings to new functions
   - Update examples if API changes

2. **Ensure tests pass**
   ```bash
   make test
   make lint
   ```

3. **Create pull request**
   - Describe your changes clearly
   - Reference any related issues
   - Include test results

4. **Code review**
   - Address reviewer feedback
   - Keep discussion professional
   - Update PR as needed

## Architecture Guidelines

### Adding New Components

When adding new components, follow these patterns:

1. **Models** (`netemulator/models/`)
   - Use Pydantic for data validation
   - Include proper type hints
   - Add validation logic

2. **Control Plane** (`netemulator/control/`)
   - Keep business logic separate from API
   - Use dependency injection
   - Handle errors gracefully

3. **Data Plane** (`netemulator/dataplane/`)
   - Minimize Mininet-specific code
   - Abstract network operations
   - Support cleanup/teardown

4. **Impairments** (`netemulator/impairments/`)
   - Make impairments reversible
   - Log all operations
   - Handle edge cases

### Testing Patterns

- Use fixtures for common setup
- Mock external dependencies
- Test error conditions
- Use parametrize for multiple cases

### Documentation

- Document complex algorithms
- Include examples in docstrings
- Update architecture diagrams
- Add new features to README

## Performance Considerations

- Profile code for bottlenecks
- Minimize syscalls in hot paths
- Use async where appropriate
- Consider memory usage for large topologies

## Security Guidelines

- Validate all user input
- Use parameterized queries
- Don't log sensitive data
- Follow principle of least privilege
- Review security implications of changes

## Questions?

- Open an issue for questions
- Check existing documentation
- Ask in team chat
- Review similar code

## License

By contributing, you agree that your contributions will be licensed under the same license as the project.

