# Update current software
apt-get update

# Get GIT for source code version control
# apt-get install git

# Helpful for Debian systems -  all packages need to compile such as gcc and g++ compilers and other utils.
apt-get install build-essential

# Install Python 3
apt-get install python3

# Package development process library to facilitate packaging Python packages
apt-get install python3-setuptools

# ensure that the python developer libraries are installed
apt-get install python3-dev

# Tkinter
apt-get install python3-tk

# Python PIP
apt-get install python3-pip

#Check python version installed
python3 --version

#Python virtual environment with same version as Python. For example, python3.7-venv for python3.7.x
apt-get install python3-venv