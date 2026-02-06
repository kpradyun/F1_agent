"""
F1 Race Engineer Agent
A comprehensive LLM-powered F1 data analysis and visualization tool
"""

from setuptools import setup, find_packages

# Read requirements
with open('requirements.txt') as f:
    requirements = [line.strip() for line in f if line.strip() and not line.startswith('#')]

# Read README for long description
with open('README.md', encoding='utf-8') as f:
    long_description = f.read()

setup(
    name='f1-race-engineer',
    version='2.3.0',
    description='LLM-powered F1 data analysis agent with interactive visualization',
    long_description=long_description,
    long_description_content_type='text/markdown',
    author='F1 Race Engineer Contributors',
    url='https://github.com/kpradyun/F1_agent',
    
    packages=find_packages(exclude=['tests', 'docs', 'examples']),
    
    install_requires=requirements,
    
    python_requires='>=3.10',
    
    entry_points={
        'console_scripts': [
            'f1-agent=main:main',
        ],
    },
    
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'Intended Audience :: Science/Research',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'Topic :: Scientific/Engineering :: Information Analysis',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        'Programming Language :: Python :: 3.12',
    ],
    
    keywords='f1 formula1 data-analysis llm agent fastf1 telemetry racing',
    
    project_urls={
        'Bug Reports': 'https://github.com/kpradyun/F1_agent/issues',
        'Source': 'https://github.com/kpradyun/F1_agent',
        'Documentation': 'https://github.com/kpradyun/F1_agent/blob/main/README.md',
    },
    
    include_package_data=True,
    zip_safe=False,
)
