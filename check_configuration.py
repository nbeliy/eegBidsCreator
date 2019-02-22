import os
import tools.cfi as cfi


def check_configuration(filename):
    
    parameters = cfi.default_parameters()
    cfi.read_parameters(parameters, filename)
    if cfi.check_configuration(parameters):
        print("File "+ filename + " seems to be correct")
        return 0
    else:
        print("File "+ filename + " contains errors")
        return 1


if __name__ == "__main__":
    os.sys.exit(check_configuration(os.sys.argv[1]))
