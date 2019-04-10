import distutils
from distutils.core import setup
import glob

bin_files = glob.glob("bin/*")
data_files = [("",["setpath.sh"])]

# The main call
setup(name='salpytools',
      version ='0.9.1',
      license = "GPL",
      description = "Python tools to connect to SAL.",
      author = "LSST, Felipe Menanteau",
      author_email = "felipe@illinois.edu",
      packages = ['salpytools'],
      package_dir = {'': 'python'},
      scripts = bin_files,
      data_files=data_files,
      )
