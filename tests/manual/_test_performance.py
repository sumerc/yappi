import sys
import time
import yappi


def generate_func(code):
    func_name = "func_{}".format(i)
    code = """def {}(*args, **kwargs): {}""".format(func_name, code)
    exec(code, {}, locals())
    return locals()[func_name]


print("Generating functions...")

funcs = []
for i in range(int(sys.argv[1])):
    funcs.append(generate_func("pass"))

print("Calling functions...")
t0 = time.time()
yappi.start()
for _, func in enumerate(funcs):
    for i in range(int(sys.argv[2])):
        func(i)
print("Elapsed %0.6f secs." % (time.time() - t0))
