from setuptools import setup

setup(entry_points = {
        'console_scripts': ['plants_server=plants.server:server'],
    },
    install_requires = [
        'Flask',
        'gpiozero',
        'prometheus-client',
        'PyYAML',
        'smbus',
    ],
    name='plants'
)
