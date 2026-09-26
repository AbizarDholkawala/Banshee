from setuptools import setup, find_packages

setup(
    name="banshee",
    version="1.0.0",
    description="Offline speech-to-text toolkit powered by faster-whisper",
    long_description=open("README.md", encoding="utf-8").read(),
    long_description_content_type="text/markdown",
    author="Banshee Contributors",
    license="MIT",
    python_requires=">=3.9",
    packages=find_packages(),
    include_package_data=True,
    package_data={
        "banshee": [
            "static/*.css",
            "static/*.js",
            "templates/*.html",
        ],
    },
    install_requires=[
        "faster-whisper>=1.0.0",
        "sounddevice>=0.4.6",
        "soundfile>=0.12.1",
        "numpy>=1.24.0",
        "flask>=3.0.0",
    ],
    entry_points={
        "console_scripts": [
            "banshee=banshee.cli:main",
        ],
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Topic :: Multimedia :: Sound/Audio :: Speech",
    ],
)
