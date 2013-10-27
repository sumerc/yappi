import yappi
import _yappi
import testutils

"""
TODO: 
 - ctx stat correctness, 
 - some stat save/load test, 
 - write more tests for complex multithreaded scenarios, such as producer/consumers ...etc.
"""

class BasicUsage(testutils.YappiUnitTestCase):
    
    def test_module_stress(self):
        self.assertRaises(_yappi.error, yappi.get_func_stats)
        self.assertRaises(_yappi.error, yappi.get_thread_stats)
        self.assertEqual(yappi.is_running(), False)
        
        yappi.start()
        self.assertRaises(_yappi.error, yappi.clear_stats)
        self.assertRaises(_yappi.error, yappi.set_clock_type, "wall")
        
        yappi.stop()
        yappi.clear_stats()
        yappi.set_clock_type("cpu")
        self.assertRaises(yappi.YappiError, yappi.set_clock_type, "dummy")
        self.assertEqual(yappi.is_running(), False)
        self.assertRaises(_yappi.error, yappi.get_func_stats)
        self.assertRaises(_yappi.error, yappi.get_thread_stats)
        yappi.clear_stats()
        yappi.clear_stats()
                
    def test_stat_sorting(self):
        pass # TODO: with test_timings
        
    def test_builtin_profiling(self):
        def a():
            import time
            time.sleep(0.4) # is a builtin function
        yappi.set_clock_type('wall')

        yappi.start(builtins=True)
        a()
        stats = yappi.get_func_stats()
        fsa = stats.find_by_name('sleep')
        self.assertTrue(fsa is not None)
        self.assertTrue(fsa.ttot > 0.3)
        
    def test_multithread_profiling(self):
        import threading
        import time
        yappi.set_clock_type('wall')
        def a():
            time.sleep(0.2)
        class Worker1(threading.Thread):
            def a(self):
                time.sleep(0.3)                
            def run(self):
                self.a()
        yappi.start(builtins=False, profile_threads=True)

        c = Worker1()
        c.start()
        c.join()        
        a()
        stats = yappi.get_func_stats()
        fsa1 = stats.find_by_name('Worker1.a')
        fsa2 = stats.find_by_name('a')
        self.assertTrue(fsa1 is not None)
        self.assertTrue(fsa2 is not None)
        self.assertTrue(fsa1.ttot > 0.2)
        self.assertTrue(fsa2.ttot > 0.1)
        
    def test_singlethread_profiling(self):
        import threading
        import time
        yappi.set_clock_type('wall')
        def a():
            time.sleep(0.2)
        class Worker1(threading.Thread):
            def a(self):
                time.sleep(0.3)
            def run(self):
                self.a()
        yappi.start(profile_threads=False)

        c = Worker1()
        c.start()
        c.join()
        a()
        stats = yappi.get_func_stats()
        fsa1 = stats.find_by_name('Worker1.a')
        fsa2 = stats.find_by_name('a')
        self.assertTrue(fsa1 is None)
        self.assertTrue(fsa2 is not None)
        self.assertTrue(fsa2.ttot > 0.1)
   
class NonRecursiveFunctions(testutils.YappiUnitTestCase):
    def test_abcd(self):
        _timings = {"a_1":6,"b_1":5,"c_1":3, "d_1":1}
        _yappi.set_test_timings(_timings)

        def a():
            b()
        def b():
            c()
        def c():
            d()
        def d():
            pass
        testutils.run_with_yappi(a)
        stats = yappi.get_func_stats()
        fsa = stats.find_by_name('a')
        fsb = stats.find_by_name('b')
        fsc = stats.find_by_name('c')
        fsd = stats.find_by_name('d')
        cfsab = testutils.get_child_stat(fsa, fsb)
        cfsbc = testutils.get_child_stat(fsb, fsc)
        cfscd = testutils.get_child_stat(fsc, fsd)

        self.assertEqual(fsa.ttot , 6)
        self.assertEqual(fsa.tsub , 1)
        self.assertEqual(fsb.ttot , 5)
        self.assertEqual(fsb.tsub , 2)
        self.assertEqual(fsc.ttot , 3)
        self.assertEqual(fsc.tsub , 2)
        self.assertEqual(fsd.ttot , 1)
        self.assertEqual(fsd.tsub , 1)
        self.assertEqual(cfsab.ttot , 5)
        self.assertEqual(cfsab.tsub , 2)
        self.assertEqual(cfsbc.ttot , 3)
        self.assertEqual(cfsbc.tsub , 2)
        self.assertEqual(cfscd.ttot , 1)
        self.assertEqual(cfscd.tsub , 1)
        
    def test_stop_in_middle(self):
        import time
        _timings = {"a_1":6,"b_1":4}
        _yappi.set_test_timings(_timings)

        def a():
            b()
            yappi.stop()
            
        def b():    
            time.sleep(0.2)

        yappi.start()
        a()
        stats = yappi.get_func_stats()
        fsa = stats.find_by_name('a')
        fsb = stats.find_by_name('b')

        self.assertEqual(fsa.ncall , 1)
        self.assertEqual(fsa.nactualcall, 0)
        self.assertEqual(fsa.ttot , 0) # no call_leave called
        self.assertEqual(fsa.tsub , 0) # no call_leave called
        self.assertEqual(fsb.ttot , 4) 
        
class RecursiveFunctions(testutils.YappiUnitTestCase): 
    def test_fibonacci(self):
        def fib(n):
           if n > 1:
               return fib(n-1) + fib(n-2)
           else:
               return n
        testutils.run_with_yappi(fib, 22)
        stats = yappi.get_func_stats()
        fs = stats.find_by_name('fib')
        self.assertEqual(fs.ncall, 57313)
        self.assertEqual(fs.ttot, fs.tsub)
        
    def test_abcadc(self):
        _timings = {"a_1":20,"b_1":19,"c_1":17, "a_2":13, "d_1":12, "c_2":10, "a_3":5}
        _yappi.set_test_timings(_timings)
            
        def a(n):
            if n == 3:
                return
            if n == 1 + 1:
                d(n)
            else:
                b(n)    
        def b(n):        
            c(n)    
        def c(n):
            a(n+1)    
        def d(n):
            c(n)
        testutils.run_with_yappi(a, 1)
        stats = yappi.get_func_stats()
        fsa = stats.find_by_name('a')
        fsb = stats.find_by_name('b')
        fsc = stats.find_by_name('c')
        fsd = stats.find_by_name('d')
        self.assertEqual(fsa.ncall, 3)
        self.assertEqual(fsa.nactualcall, 1)
        self.assertEqual(fsa.ttot, 20)
        self.assertEqual(fsa.tsub, 7)
        self.assertEqual(fsb.ttot, 19)
        self.assertEqual(fsb.tsub, 2)
        self.assertEqual(fsc.ttot, 17)
        self.assertEqual(fsc.tsub, 9)
        self.assertEqual(fsd.ttot, 12)
        self.assertEqual(fsd.tsub, 2)
        cfsca = testutils.get_child_stat(fsc, fsa)
        self.assertEqual(cfsca.nactualcall, 0)
        self.assertEqual(cfsca.ncall, 2)
        self.assertEqual(cfsca.ttot, 13)
        self.assertEqual(cfsca.tsub, 6)
        
    def test_aaaa(self):
        _timings = {"d_1":9, "d_2":7, "d_3":3, "d_4":2}
        _yappi.set_test_timings(_timings)
        def d(n):
            if n == 3:
                return
            d(n+1)
        testutils.run_with_yappi(d, 0)
        stats = yappi.get_func_stats()
        fsd = stats.find_by_name('d')
        self.assertEqual(fsd.ncall , 4)
        self.assertEqual(fsd.nactualcall , 1)
        self.assertEqual(fsd.ttot , 9)
        self.assertEqual(fsd.tsub , 9)
        cfsdd = testutils.get_child_stat(fsd, fsd)
        self.assertEqual(cfsdd.ttot , 7)
        self.assertEqual(cfsdd.tsub , 7)
        self.assertEqual(cfsdd.ncall , 3)
        self.assertEqual(cfsdd.nactualcall , 0)
        
    def test_abcabc(self):
        _timings = {"a_1":20,"b_1":19,"c_1":17, "a_2":13, "b_2":11, "c_2":9, "a_3":6}
        _yappi.set_test_timings(_timings)
            
        def a(n):
            if n == 3:
                return
            else:
                b(n)
        def b(n):        
            c(n)    
        def c(n):
            a(n+1)    

        testutils.run_with_yappi(a, 1)
        stats = yappi.get_func_stats()
        fsa = stats.find_by_name('a')
        fsb = stats.find_by_name('b')
        fsc = stats.find_by_name('c')
        self.assertEqual(fsa.ncall , 3)
        self.assertEqual(fsa.nactualcall , 1)
        self.assertEqual(fsa.ttot , 20)
        self.assertEqual(fsa.tsub , 9)
        self.assertEqual(fsb.ttot , 19)
        self.assertEqual(fsb.tsub , 4)
        self.assertEqual(fsc.ttot , 17)
        self.assertEqual(fsc.tsub , 7)
        cfsab = testutils.get_child_stat(fsa, fsb)
        cfsbc = testutils.get_child_stat(fsb, fsc)
        cfsca = testutils.get_child_stat(fsc, fsa)
        self.assertEqual(cfsab.ttot , 19)
        self.assertEqual(cfsab.tsub , 4)
        self.assertEqual(cfsbc.ttot , 17)
        self.assertEqual(cfsbc.tsub , 7)
        self.assertEqual(cfsca.ttot , 13)
        self.assertEqual(cfsca.tsub , 8)
        
    def test_abcbca(self):
        _timings = {"a_1":10,"b_1":9,"c_1":7,"b_2":4,"c_2":2,"a_2":1}
        _yappi.set_test_timings(_timings)
        self._ncall = 1
        def a():
            if self._ncall == 1:
                b()
            else:
                return
        def b():
            c()
        def c():
            if self._ncall == 1:
                self._ncall += 1
                b()
            else:
                a()                
        testutils.run_with_yappi(a)
        stats = yappi.get_func_stats()
        fsa = stats.find_by_name('a')
        fsb = stats.find_by_name('b')
        fsc = stats.find_by_name('c')
        cfsab = testutils.get_child_stat(fsa, fsb)
        cfsbc = testutils.get_child_stat(fsb, fsc)
        cfsca = testutils.get_child_stat(fsc, fsa)
        self.assertEqual(fsa.ttot , 10)
        self.assertEqual(fsa.tsub , 2)
        self.assertEqual(fsb.ttot , 9)
        self.assertEqual(fsb.tsub , 4)
        self.assertEqual(fsc.ttot , 7)
        self.assertEqual(fsc.tsub , 4)
        self.assertEqual(cfsab.ttot , 9)
        self.assertEqual(cfsab.tsub , 2)
        self.assertEqual(cfsbc.ttot , 7)
        self.assertEqual(cfsbc.tsub , 4)
        self.assertEqual(cfsca.ttot , 1)
        self.assertEqual(cfsca.tsub , 1)
        self.assertEqual(cfsca.ncall , 1)
        self.assertEqual(cfsca.nactualcall , 0)

    def test_aabccb(self):
        _timings = {"a_1":13,"a_2":11,"b_1":9,"c_1":5,"c_2":3,"b_2":1}
        _yappi.set_test_timings(_timings)
        self._ncall = 1
        def a():
            if self._ncall == 1:
                self._ncall += 1
                a()
            else:
                b()
        def b():
            if self._ncall == 3:
                return
            else:
                c()
        def c():
            if self._ncall == 2:
                self._ncall += 1
                c()
            else:
                b()
                
        testutils.run_with_yappi(a)
        stats = yappi.get_func_stats()
        fsa = stats.find_by_name('a')
        fsb = stats.find_by_name('b')
        fsc = stats.find_by_name('c')
        cfsaa = testutils.get_child_stat(fsa, fsa)
        cfsab = testutils.get_child_stat(fsa, fsb)
        cfsbc = testutils.get_child_stat(fsb, fsc)
        cfscc = testutils.get_child_stat(fsc, fsc)
        cfscb = testutils.get_child_stat(fsc, fsb)
        self.assertEqual(fsb.ttot , 9)
        self.assertEqual(fsb.tsub , 5)
        self.assertEqual(cfsbc.ttot , 5)
        self.assertEqual(cfsbc.tsub , 2)
        self.assertEqual(fsa.ttot , 13)
        self.assertEqual(fsa.tsub , 4)
        self.assertEqual(cfsab.ttot , 9)
        self.assertEqual(cfsab.tsub , 4)
        self.assertEqual(cfsaa.ttot , 11)
        self.assertEqual(cfsaa.tsub , 2)
        self.assertEqual(fsc.ttot , 5)
        self.assertEqual(fsc.tsub , 4)

    def test_abaa(self):
        _timings = {"a_1":13,"b_1":10,"a_2":9,"a_3":5}
        _yappi.set_test_timings(_timings)

        self._ncall = 1
        def a():
            if self._ncall == 1:
                b()
            elif self._ncall == 2:
                self._ncall += 1
                a()
            else:
                return
        def b():
            self._ncall += 1
            a()
            
        testutils.run_with_yappi(a)
        stats = yappi.get_func_stats()
        fsa = stats.find_by_name('a')
        fsb = stats.find_by_name('b')
        cfsaa = testutils.get_child_stat(fsa, fsa)
        cfsba = testutils.get_child_stat(fsb, fsa)
        self.assertEqual(fsb.ttot , 10)
        self.assertEqual(fsb.tsub , 1)
        self.assertEqual(fsa.ttot , 13)
        self.assertEqual(fsa.tsub , 12)
        self.assertEqual(cfsaa.ttot , 5)
        self.assertEqual(cfsaa.tsub , 5)
        self.assertEqual(cfsba.ttot , 9)
        self.assertEqual(cfsba.tsub , 4)
    
    def test_aabb(self):
        _timings = {"a_1":13,"a_2":10,"b_1":9,"b_2":5}
        _yappi.set_test_timings(_timings)

        self._ncall = 1
        def a():
            if self._ncall == 1:
                self._ncall += 1
                a()
            elif self._ncall == 2:        
                b()
            else:
                return
        def b():
            if self._ncall == 2:
                self._ncall += 1
                b()
            else:
                return
            
        testutils.run_with_yappi(a)
        stats = yappi.get_func_stats()
        fsa = stats.find_by_name('a')
        fsb = stats.find_by_name('b')
        cfsaa = testutils.get_child_stat(fsa, fsa)
        cfsab = testutils.get_child_stat(fsa, fsb)
        cfsbb = testutils.get_child_stat(fsb, fsb)
        self.assertEqual(fsa.ttot , 13)
        self.assertEqual(fsa.tsub , 4)
        self.assertEqual(fsb.ttot , 9)
        self.assertEqual(fsb.tsub , 9)
        self.assertEqual(cfsaa.ttot , 10)
        self.assertEqual(cfsaa.tsub , 1)
        self.assertEqual(cfsab.ttot , 9)
        self.assertEqual(cfsab.tsub , 4)
        self.assertEqual(cfsbb.ttot , 5)
        self.assertEqual(cfsbb.tsub , 5)

    def test_abbb(self):
        _timings = {"a_1":13,"b_1":10,"b_2":6,"b_3":1}
        _yappi.set_test_timings(_timings)

        self._ncall = 1
        def a():
            if self._ncall == 1:
                b()
        def b():
            if self._ncall == 3:
                return
            self._ncall += 1
            b()
            
        testutils.run_with_yappi(a)
        stats = yappi.get_func_stats()
        fsa = stats.find_by_name('a')
        fsb = stats.find_by_name('b')
        cfsab = testutils.get_child_stat(fsa, fsb)
        cfsbb = testutils.get_child_stat(fsb, fsb)
        self.assertEqual(fsa.ttot , 13)
        self.assertEqual(fsa.tsub , 3)
        self.assertEqual(fsb.ttot , 10)
        self.assertEqual(fsb.tsub , 10)
        self.assertEqual(fsb.ncall , 3)
        self.assertEqual(fsb.nactualcall , 1)
        self.assertEqual(cfsab.ttot , 10)
        self.assertEqual(cfsab.tsub , 4)
        self.assertEqual(cfsbb.ttot , 6)
        self.assertEqual(cfsbb.tsub , 6)
        self.assertEqual(cfsbb.nactualcall , 0)
        self.assertEqual(cfsbb.ncall , 2)
    
    def test_aaab(self):
        _timings = {"a_1":13,"a_2":10,"a_3":6,"b_1":1}
        _yappi.set_test_timings(_timings)

        self._ncall = 1
        def a():
            if self._ncall == 3:
                b()
                return
            self._ncall += 1
            a()
        def b():
            return
            
        testutils.run_with_yappi(a)
        stats = yappi.get_func_stats()
        fsa = stats.find_by_name('a')
        fsb = stats.find_by_name('b')
        cfsaa = testutils.get_child_stat(fsa, fsa)
        cfsab = testutils.get_child_stat(fsa, fsb)
        self.assertEqual(fsa.ttot , 13)
        self.assertEqual(fsa.tsub , 12)
        self.assertEqual(fsb.ttot , 1)
        self.assertEqual(fsb.tsub , 1)
        self.assertEqual(cfsaa.ttot , 10)
        self.assertEqual(cfsaa.tsub , 9)
        self.assertEqual(cfsab.ttot , 1)
        self.assertEqual(cfsab.tsub , 1)
    
    def test_abab(self):
        _timings = {"a_1":13,"b_1":10,"a_2":6,"b_2":1}
        _yappi.set_test_timings(_timings)

        self._ncall = 1
        def a():
            b()
        def b():
            if self._ncall == 2:
                return
            self._ncall += 1
            a()
            
        testutils.run_with_yappi(a)
        stats = yappi.get_func_stats()
        fsa = stats.find_by_name('a')
        fsb = stats.find_by_name('b')
        cfsab = testutils.get_child_stat(fsa, fsb)
        cfsba = testutils.get_child_stat(fsb, fsa)
        self.assertEqual(fsa.ttot , 13)
        self.assertEqual(fsa.tsub , 8)
        self.assertEqual(fsb.ttot , 10)
        self.assertEqual(fsb.tsub , 5)
        self.assertEqual(cfsab.ttot , 10)
        self.assertEqual(cfsab.tsub , 5)
        self.assertEqual(cfsab.ncall , 2)
        self.assertEqual(cfsab.nactualcall , 1)
        self.assertEqual(cfsba.ttot , 6)
        self.assertEqual(cfsba.tsub , 5)