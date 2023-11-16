import sys
import time
import yappi


def generate_func(code):
    func_name = f"func_{i}"
    code = f"""def {func_name}(*args, **kwargs): {code}"""
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
print(f"Elapsed {time.time() - t0:0.6f} secs.")
