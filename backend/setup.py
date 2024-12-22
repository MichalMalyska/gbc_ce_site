from setuptools import find_namespace_packages, setup

setup(
    name="course_api",
    version="0.1.0",
    packages=find_namespace_packages(include=["config.*", "courses.*"]),
    install_requires=[
        "django>=5.0.0",
        "djangorestframework>=3.14.0",
        "django-cors-headers>=4.3.1",
    ],
)
