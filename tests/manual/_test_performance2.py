import sys
import time
import yappi


def generate_func(func_name, code):
    code = f"""def {func_name}(*args, **kwargs): {code}"""
    exec(code, globals(), locals())
    func = locals()[func_name]
    globals()[func.__name__] = func
    return func


print("Generating functions...")

FUNC_COUNT = int(sys.argv[1])
MAX_STACK_DEPTH = int(sys.argv[2])

top_level_funcs = []

# todo: generate functions that are N stack depth
for i in range(FUNC_COUNT):
    func = generate_func(f'func_{i}', "pass")
    for k in range(MAX_STACK_DEPTH):
        func = generate_func(f'func_{i}_{k}', func.__name__ + '()')
    top_level_funcs.append(func)

#print(globals())
print("Calling functions...")
t0 = time.time()
#yappi.start()
for f in top_level_funcs:
    f(i)
print(f"Elapsed {time.time() - t0:0.6f} secs")
#yappi.get_func_stats().print_all()
