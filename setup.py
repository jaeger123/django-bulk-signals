from setuptools import setup, find_packages

setup(
    name='django-bulk-signals',
    version='0.1.0',
    packages=find_packages(),
    install_requires=[
        'Django>=3.2',
    ],
    author='Akarsh Sharma',
    author_email='akarsh1998@gmail.com',
    description='Custom Django signals for update, bulk update/create operations with field tracking',
    long_description=open('README.md').read(),
    long_description_content_type='text/markdown',
    url='https://github.com/jaeger123/django-bulk-signals',  # Optional
    classifiers=[
        'Framework :: Django',
        'Programming Language :: Python :: 3',
        'Operating System :: OS Independent',
        'License :: OSI Approved :: MIT License',
    ],
    python_requires='>=3.8',
)
