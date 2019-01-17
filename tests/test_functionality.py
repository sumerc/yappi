import os
import sys
import time
import threading
import yappi
import _yappi
import utils
import multiprocessing # added to fix http://bugs.python.org/issue15881 for > Py2.6
import subprocess 

if sys.version_info < (2, 7): # use unittest2 for < Py2.7
    import unittest2 as _unittest
else:
    import unittest as _unittest

class BasicUsage(utils.YappiUnitTestCase):

    def test_filter(self):
        def a(): pass
        def b(): a()
        def c(): b()

        _TCOUNT = 5

        ts = []
        yappi.start()
        for i in range(_TCOUNT):
            t = threading.Thread(target=c)
            t.start()
            ts.append(t)

        for t in ts:
            t.join()

        yappi.stop()

        fstats = yappi.get_func_stats(filter={"ctx_id":9})
        self.assertTrue(fstats.empty())
        fstats = yappi.get_func_stats(filter={"ctx_id":0, "name":"c"}) # main thread
        self.assertTrue(fstats.empty())

        for i in range(1, _TCOUNT):
            fstats = yappi.get_func_stats(filter={"ctx_id":i, "name":"a", 
                "ncall":1})
            self.assertEqual(fstats.pop().ncall, 1)
            fstats = yappi.get_func_stats(filter={"ctx_id":i, "name":"b"})
            self.assertEqual(fstats.pop().ncall, 1)
            fstats = yappi.get_func_stats(filter={"ctx_id":i, "name":"c"})
            self.assertEqual(fstats.pop().ncall, 1)

    def test_print_formatting(self):
        def a():
            pass
        def b():
            a()
        
        func_cols={1:("name",48), 0:("ncall", 5), 2:("tsub", 8),}
        thread_cols = {1:("name", 48), 0:("ttot", 8), }
        
        yappi.start()
        a(); b();
        yappi.stop()
        fs = yappi.get_func_stats()
        cs = fs[1].children
        ts = yappi.get_thread_stats()
        #fs.print_all(out=sys.stderr, columns={1:("name", 70), })
        #cs.print_all(out=sys.stderr, columns=func_cols)
        #ts.print_all(out=sys.stderr, columns=thread_cols)
        #cs.print_all(out=sys.stderr, columns={})
        
        self.assertRaises(yappi.YappiError, fs.print_all, columns={1:("namee",9)})
        self.assertRaises(yappi.YappiError, cs.print_all, columns={1:("dd",0)})
        self.assertRaises(yappi.YappiError, ts.print_all, columns={1:("tidd",0)})
   
    def test_get_clock(self):
        yappi.set_clock_type('cpu')
        self.assertEqual('cpu', yappi.get_clock_type())
        clock_info = yappi.get_clock_info()
        self.assertTrue('api' in clock_info)
        self.assertTrue('resolution' in clock_info)

        yappi.set_clock_type('wall')
        self.assertEqual('wall', yappi.get_clock_type())

        t0 = yappi.get_clock_time()
        time.sleep(0.1)
        duration = yappi.get_clock_time() - t0
        self.assertTrue(0.05 < duration < 0.2)

    def test_profile_decorator(self):

        def aggregate(func, stats):
            fname = "%s.profile" % (func.__name__)
            try: 
                stats.add(fname)
            except IOError:
                pass
            stats.save(fname)
            raise Exception("messing around")
             
        @yappi.profile(return_callback=aggregate)
        def a(x, y):
            if x+y == 25:
                raise Exception("")
            return x+y
        def b():
            pass
        try:
            os.remove("a.profile") # remove the one from prev test, if available
        except:
            pass
        
        # global profile is on to mess things up
        yappi.start()
        b()
        
        # assert functionality and call function at same time
        try:
            self.assertEqual(a(1, 2), 3)
        except:
            pass
        try:
            self.assertEqual(a(2, 5), 7)
        except:
            pass
        try:    
            a(4, 21)
        except:
            pass
        stats = yappi.get_func_stats().add("a.profile")
        fsa = utils.find_stat_by_name(stats, 'a')
        self.assertEqual(fsa.ncall, 3)
        self.assertEqual(len(stats), 1) # b() should be cleared out.
        
        @yappi.profile(return_callback=aggregate)
        def count_down_rec(n):
            if n == 0:
                return
            count_down_rec(n-1)
        
        try:
            os.remove("count_down_rec.profile") # remove the one from prev test, if available
        except:
            pass
        
        try:    
            count_down_rec(4)
        except:
            pass
        try:    
            count_down_rec(3)
        except:
            pass
        
        stats = yappi.YFuncStats("count_down_rec.profile")
        fsrec = utils.find_stat_by_name(stats, 'count_down_rec')
        self.assertEqual(fsrec.ncall, 9)
        self.assertEqual(fsrec.nactualcall, 2)
        
    def test_strip_dirs(self):
        def a():
            pass
        stats = utils.run_and_get_func_stats(a,)
        stats.strip_dirs()
        fsa = utils.find_stat_by_name(stats, "a")
        self.assertEqual(fsa.module, os.path.basename(fsa.module))

    def test_run_as_script(self):
        import re
        p = subprocess.Popen([sys.executable, 'yappi.py', 'tests/run_as_script.py'],
                             stdout=subprocess.PIPE)
        out, err = p.communicate()
        self.assertEqual(p.returncode, 0)
        func_stats, thread_stats = re.split(b'name\s+id\s+tid\s+ttot\s+scnt\s*\n', out)
        self.assertTrue(b'FancyThread' in thread_stats)
        
    def test_yappi_overhead(self):
        LOOP_COUNT = 100000
        def a(): pass
        def b():
            for i in range(LOOP_COUNT): a()
        t0 = time.time()
        yappi.start()
        b()
        yappi.stop()
        time_with_yappi = time.time() - t0
        t0 = time.time()
        b()
        time_without_yappi = time.time() - t0
        if time_without_yappi == 0:
            time_without_yappi = 0.000001
            
        # in latest v0.82, I calculated this as close to "7.0" in my machine.
        # however, %83 of this overhead is coming from tickcount(). The other %17
        # seems to have been evenly distributed to the internal bookkeeping 
        # structures/algorithms which seems acceptable. Note that our test only 
        # tests one function being profiled at-a-time in a short interval. 
        # profiling high number of functions in a small time
        # is a different beast, (which is pretty unlikely in most applications)
        # So as a conclusion: I cannot see any optimization window for Yappi that
        # is worth implementing as we will only optimize %17 of the time.
        sys.stderr.write("\r\nYappi puts %0.1f times overhead to the profiled application in average.\r\n" % \
            (time_with_yappi / time_without_yappi))        
        
    def test_clear_stats_while_running(self):
        def a():            
            pass
        yappi.start()
        a()
        yappi.clear_stats()
        a()
        stats = yappi.get_func_stats()
        fsa = utils.find_stat_by_name(stats, 'a')
        self.assertEqual(fsa.ncall, 1)
        
    def test_generator(self):
        def _gen(n):
            while(n > 0):
                yield n
                n -= 1
        yappi.start()
        for x in _gen(5):
            pass
        self.assertTrue(yappi.convert2pstats(yappi.get_func_stats()) is not None)
        
    def test_slice_child_stats_and_strip_dirs(self):
        def b(): 
            for i in range(10000000): pass
        def a():
            b()
        yappi.start(builtins=True)
        a()
        stats = yappi.get_func_stats()
        fsa = utils.find_stat_by_name(stats, 'a')
        fsb = utils.find_stat_by_name(stats, 'b')
        self.assertTrue(fsa.children[0:1] is not None)
        prev_afullname = fsa.full_name
        prev_bchildfullname = fsa.children[fsb].full_name
        stats.strip_dirs()
        self.assertTrue(len(prev_afullname) > len(fsa.full_name))
        self.assertTrue(len(prev_bchildfullname) > len(fsa.children[fsb].full_name))
        
    def test_children_stat_functions(self):
        _timings = {"a_1":5, "b_1":3, "c_1":1}
        _yappi._set_test_timings(_timings)
        def b(): 
            pass
        def c():
            pass
        def a():
            b()
            c()
        yappi.start()
        a()
        b() # non-child call
        c() # non-child call
        stats = yappi.get_func_stats()
        fsa = utils.find_stat_by_name(stats, 'a')
        childs_of_a = fsa.children.get().sort("tavg", "desc")
        prev_item = None
        for item in childs_of_a:
            if prev_item:
                self.assertTrue(prev_item.tavg > item.tavg)
            prev_item = item
        childs_of_a.sort("name", "desc")
        prev_item = None
        for item in childs_of_a:
            if prev_item:
                self.assertTrue(prev_item.name > item.name)
            prev_item = item
        childs_of_a.clear()
        self.assertTrue(childs_of_a.empty())
            
    def test_no_stats_different_clock_type_load(self):
        def a(): pass
        yappi.start()
        a()
        yappi.stop()
        yappi.get_func_stats().save("ystats1.ys")
        yappi.clear_stats()
        yappi.set_clock_type("WALL")
        yappi.start()
        yappi.stop()
        stats = yappi.get_func_stats().add("ystats1.ys")
        fsa = utils.find_stat_by_name(stats, 'a')
        self.assertTrue(fsa is not None)
      
    def test_subsequent_profile(self):
        _timings = {"a_1":1, "b_1":1}
        _yappi._set_test_timings(_timings)
        def a(): pass
        def b(): pass
        
        yappi.start()
        a()
        yappi.stop()
        yappi.start()
        b()
        yappi.stop()
        stats = yappi.get_func_stats()
        fsa = utils.find_stat_by_name(stats, 'a')
        fsb = utils.find_stat_by_name(stats, 'b')
        self.assertTrue(fsa is not None)
        self.assertTrue(fsb is not None)
        self.assertEqual(fsa.ttot, 1)
        self.assertEqual(fsb.ttot, 1)
             
    def test_lambda(self):
        f = lambda : time.sleep(0.3)
        yappi.set_clock_type("wall")
        yappi.start()
        f()
        stats = yappi.get_func_stats()
        fsa = utils.find_stat_by_name(stats, '<lambda>')
        self.assertTrue(fsa.ttot > 0.1)
        
    def test_module_stress(self):
        self.assertEqual(yappi.is_running(), False)
        
        yappi.start()
        yappi.clear_stats()
        self.assertRaises(_yappi.error, yappi.set_clock_type, "wall")
        
        yappi.stop()
        yappi.clear_stats()
        yappi.set_clock_type("cpu")
        self.assertRaises(yappi.YappiError, yappi.set_clock_type, "dummy")
        self.assertEqual(yappi.is_running(), False)
        yappi.clear_stats()
        yappi.clear_stats()
                
    def test_stat_sorting(self):
        _timings = {"a_1":13,"b_1":10,"a_2":6,"b_2":1}
        _yappi._set_test_timings(_timings)

        self._ncall = 1
        def a():
            b()
        def b():
            if self._ncall == 2:
                return
            self._ncall += 1
            a()
            
        stats = utils.run_and_get_func_stats(a)
        stats = stats.sort("totaltime", "desc")
        prev_stat = None
        for stat in stats:
            if prev_stat:
                self.assertTrue(prev_stat.ttot >= stat.ttot)
            prev_stat = stat
        stats = stats.sort("totaltime", "asc")
        prev_stat = None
        for stat in stats:
            if prev_stat:
                self.assertTrue(prev_stat.ttot <= stat.ttot)
            prev_stat = stat
        stats = stats.sort("avgtime", "asc")
        prev_stat = None
        for stat in stats:
            if prev_stat:
                self.assertTrue(prev_stat.tavg <= stat.tavg)
            prev_stat = stat
        stats = stats.sort("name", "asc")
        prev_stat = None
        for stat in stats:
            if prev_stat:
                self.assertTrue(prev_stat.name <= stat.name)
            prev_stat = stat
        stats = stats.sort("subtime", "asc")
        prev_stat = None
        for stat in stats:
            if prev_stat:
                self.assertTrue(prev_stat.tsub <= stat.tsub)
            prev_stat = stat
          
        self.assertRaises(yappi.YappiError, stats.sort, "invalid_func_sorttype_arg")
        self.assertRaises(yappi.YappiError, stats.sort, "totaltime", "invalid_func_sortorder_arg")

    def test_start_flags(self):
        self.assertEqual(_yappi._get_start_flags(), None)
        yappi.start()
        def a(): pass
        a()
        self.assertEqual(_yappi._get_start_flags()["profile_builtins"], 0)
        self.assertEqual(_yappi._get_start_flags()["profile_multithread"], 1)
        self.assertEqual(len(yappi.get_thread_stats()), 1) 
        
    def test_builtin_profiling(self):
        def a():
            time.sleep(0.4) # is a builtin function
        yappi.set_clock_type('wall')

        yappi.start(builtins=True)
        a()
        stats = yappi.get_func_stats()
        fsa = utils.find_stat_by_name(stats, 'sleep')
        self.assertTrue(fsa is not None)
        self.assertTrue(fsa.ttot > 0.3)
        yappi.stop()
        yappi.clear_stats()
        
        def a():
            pass
        yappi.start()
        t = threading.Thread(target=a)
        t.start()
        t.join()
        stats = yappi.get_func_stats()
        
    def test_singlethread_profiling(self):
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
        fsa1 = utils.find_stat_by_name(stats, 'Worker1.a')
        fsa2 = utils.find_stat_by_name(stats, 'a')
        self.assertTrue(fsa1 is None)
        self.assertTrue(fsa2 is not None)
        self.assertTrue(fsa2.ttot > 0.1)

    def test_run(self):

        def profiled():
            pass

        yappi.clear_stats()
        try:
            with yappi.run():
                profiled()
            stats = yappi.get_func_stats()
        finally:
            yappi.clear_stats()

        self.assertIsNotNone(utils.find_stat_by_name(stats, 'profiled'))

    def test_run_recursive(self):

        def profiled():
            pass

        def not_profiled():
            pass

        yappi.clear_stats()
        try:
            with yappi.run():
                with yappi.run():
                    profiled()
                # Profiling stopped here
                not_profiled()
            stats = yappi.get_func_stats()
        finally:
            yappi.clear_stats()

        self.assertIsNotNone(utils.find_stat_by_name(stats, 'profiled'))
        self.assertIsNone(utils.find_stat_by_name(stats, 'not_profiled'))


class StatSaveScenarios(utils.YappiUnitTestCase):

    def test_pstats_conversion(self):
        def pstat_id(fs):
            return (fs.module, fs.lineno, fs.name)
        
        def a():
            d()
        def b():
            d()
        def c():
            pass
        def d():
            pass
            
        _timings = {"a_1":12,"b_1":7,"c_1":5,"d_1":2}
        _yappi._set_test_timings(_timings)            
        stats = utils.run_and_get_func_stats(a,)
        stats.strip_dirs()    
        stats.save("a1.pstats", type="pstat")
        fsa_pid = pstat_id(utils.find_stat_by_name(stats, "a"))
        fsd_pid = pstat_id(utils.find_stat_by_name(stats, "d"))
        yappi.clear_stats()
        _yappi._set_test_timings(_timings)
        stats = utils.run_and_get_func_stats(a,)
        stats.strip_dirs()
        stats.save("a2.pstats", type="pstat")
        yappi.clear_stats()
        _yappi._set_test_timings(_timings)
        stats = utils.run_and_get_func_stats(b,)        
        stats.strip_dirs()
        stats.save("b1.pstats", type="pstat")
        fsb_pid = pstat_id(utils.find_stat_by_name(stats, "b"))
        yappi.clear_stats()
        _yappi._set_test_timings(_timings)
        stats = utils.run_and_get_func_stats(c,)
        stats.strip_dirs()
        stats.save("c1.pstats", type="pstat")
        fsc_pid = pstat_id(utils.find_stat_by_name(stats, "c"))
        
        # merge saved stats and check pstats values are correct
        import pstats
        p = pstats.Stats('a1.pstats', 'a2.pstats', 'b1.pstats', 'c1.pstats')
        p.strip_dirs()
        # ct = ttot, tt = tsub
        (cc, nc, tt, ct, callers) = p.stats[fsa_pid]
        self.assertEqual(cc, nc, 2)
        self.assertEqual(tt, 20)
        self.assertEqual(ct, 24)
        (cc, nc, tt, ct, callers) = p.stats[fsd_pid]
        self.assertEqual(cc, nc, 3)
        self.assertEqual(tt, 6)
        self.assertEqual(ct, 6)        
        self.assertEqual(len(callers), 2)
        (cc, nc, tt, ct) = callers[fsa_pid]
        self.assertEqual(cc, nc, 2)
        self.assertEqual(tt, 4)
        self.assertEqual(ct, 4)
        (cc, nc, tt, ct) = callers[fsb_pid]
        self.assertEqual(cc, nc, 1)
        self.assertEqual(tt, 2)
        self.assertEqual(ct, 2)        
        
    def test_merge_stats(self):
        _timings = {"a_1":15,"b_1":14,"c_1":12,"d_1":10,"e_1":9,"f_1":7,"g_1":6,"h_1":5,"i_1":1}
        _yappi._set_test_timings(_timings)
        def a():
            b()
        def b():
            c()
        def c():
            d()
        def d():
            e()
        def e():
            f()
        def f():
            g()
        def g():
            h()
        def h():
            i()
        def i():
            pass     
        yappi.start()
        a()
        a()
        yappi.stop()
        stats = yappi.get_func_stats()
        self.assertRaises(NotImplementedError, stats.save, "", "INVALID_SAVE_TYPE")
        stats.save("ystats2.ys")
        yappi.clear_stats()
        _yappi._set_test_timings(_timings)
        yappi.start()
        a()        
        stats = yappi.get_func_stats().add("ystats2.ys")
        fsa = utils.find_stat_by_name(stats, "a")
        fsb = utils.find_stat_by_name(stats, "b")
        fsc = utils.find_stat_by_name(stats, "c")
        fsd = utils.find_stat_by_name(stats, "d")
        fse = utils.find_stat_by_name(stats, "e")
        fsf = utils.find_stat_by_name(stats, "f")
        fsg = utils.find_stat_by_name(stats, "g")
        fsh = utils.find_stat_by_name(stats, "h")
        fsi = utils.find_stat_by_name(stats, "i")
        self.assertEqual(fsa.ttot, 45)
        self.assertEqual(fsa.ncall, 3)
        self.assertEqual(fsa.nactualcall, 3)
        self.assertEqual(fsa.tsub, 3)
        self.assertEqual(fsa.children[fsb].ttot, fsb.ttot)
        self.assertEqual(fsa.children[fsb].tsub, fsb.tsub)
        self.assertEqual(fsb.children[fsc].ttot, fsc.ttot)
        self.assertEqual(fsb.children[fsc].tsub, fsc.tsub)
        self.assertEqual(fsc.tsub, 6)
        self.assertEqual(fsc.children[fsd].ttot, fsd.ttot)
        self.assertEqual(fsc.children[fsd].tsub, fsd.tsub)        
        self.assertEqual(fsd.children[fse].ttot, fse.ttot)
        self.assertEqual(fsd.children[fse].tsub, fse.tsub) 
        self.assertEqual(fse.children[fsf].ttot, fsf.ttot)
        self.assertEqual(fse.children[fsf].tsub, fsf.tsub) 
        self.assertEqual(fsf.children[fsg].ttot, fsg.ttot)
        self.assertEqual(fsf.children[fsg].tsub, fsg.tsub) 
        self.assertEqual(fsg.ttot, 18)
        self.assertEqual(fsg.tsub, 3)
        self.assertEqual(fsg.children[fsh].ttot, fsh.ttot)
        self.assertEqual(fsg.children[fsh].tsub, fsh.tsub)
        self.assertEqual(fsh.ttot, 15)
        self.assertEqual(fsh.tsub, 12)
        self.assertEqual(fsh.tavg, 5)
        self.assertEqual(fsh.children[fsi].ttot, fsi.ttot)
        self.assertEqual(fsh.children[fsi].tsub, fsi.tsub) 
        #stats.debug_print()

    def test_merge_multithreaded_stats(self):
        import _yappi
        timings = {"a_1":2, "b_1":1}
        _yappi._set_test_timings(timings)
        def a(): pass
        def b(): pass
        yappi.start()
        t = threading.Thread(target=a)
        t.start()
        t.join()
        t = threading.Thread(target=b)
        t.start()
        t.join()
        yappi.get_func_stats().save("ystats1.ys")
        yappi.clear_stats()
        _yappi._set_test_timings(timings)
        self.assertEqual(len(yappi.get_func_stats()), 0)
        self.assertEqual(len(yappi.get_thread_stats()), 1)
        t = threading.Thread(target=a)
        t.start()
        t.join()
        
        self.assertEqual(_yappi._get_start_flags()["profile_builtins"], 0)
        self.assertEqual(_yappi._get_start_flags()["profile_multithread"], 1)
        yappi.get_func_stats().save("ystats2.ys")
       
        stats = yappi.YFuncStats(["ystats1.ys", "ystats2.ys",])
        fsa = utils.find_stat_by_name(stats, "a")
        fsb = utils.find_stat_by_name(stats, "b")
        self.assertEqual(fsa.ncall, 2)
        self.assertEqual(fsb.ncall, 1)
        self.assertEqual(fsa.tsub, fsa.ttot, 4)
        self.assertEqual(fsb.tsub, fsb.ttot, 1)
        
    def test_merge_load_different_clock_types(self):
        yappi.start(builtins=True)
        def a(): b()
        def b(): c()
        def c(): pass
        t = threading.Thread(target=a)
        t.start()
        t.join()
        yappi.get_func_stats().sort("name", "asc").save("ystats1.ys")
        yappi.stop()
        yappi.clear_stats()
        yappi.start(builtins=False)
        t = threading.Thread(target=a)
        t.start()
        t.join()
        yappi.get_func_stats().save("ystats2.ys")
        yappi.stop()
        self.assertRaises(_yappi.error, yappi.set_clock_type, "wall")
        yappi.clear_stats()
        yappi.set_clock_type("wall")
        yappi.start()
        t = threading.Thread(target=a)
        t.start()
        t.join()
        yappi.get_func_stats().save("ystats3.ys")
        self.assertRaises(yappi.YappiError, yappi.YFuncStats().add("ystats1.ys").add, "ystats3.ys")
        stats = yappi.YFuncStats(["ystats1.ys", "ystats2.ys"]).sort("name")
        fsa = utils.find_stat_by_name(stats, "a")
        fsb = utils.find_stat_by_name(stats, "b")
        fsc = utils.find_stat_by_name(stats, "c")
        self.assertEqual(fsa.ncall, 2)
        self.assertEqual(fsa.ncall, fsb.ncall, fsc.ncall)
              
    def test_merge_aabab_aabbc(self):
        _timings = {"a_1":15,"a_2":14,"b_1":12,"a_3":10,"b_2":9, "c_1":4}
        _yappi._set_test_timings(_timings)
        
        def a():
            if self._ncall == 1:
                self._ncall += 1
                a()
            elif self._ncall == 5:
                self._ncall += 1
                a()
            else:
                b()
        def b():
            if self._ncall == 2:
                self._ncall += 1
                a()
            elif self._ncall == 6:
                self._ncall += 1
                b()
            elif self._ncall == 7:
                c()
            else:
                return
        def c():
            pass
        
        self._ncall = 1
        stats = utils.run_and_get_func_stats(a,)
        stats.save("ystats1.ys")
        yappi.clear_stats()
        _yappi._set_test_timings(_timings)
        #stats.print_all()
               
        self._ncall = 5
        stats = utils.run_and_get_func_stats(a,)
        stats.save("ystats2.ys")
        #stats.print_all()
        
        def a(): # same name but another function(code object)
            pass
        yappi.start()
        a()
        stats = yappi.get_func_stats().add(["ystats1.ys", "ystats2.ys"])
        #stats.print_all()        
        self.assertEqual(len(stats), 4)
        
        fsa = None
        for stat in stats:
            if stat.name == "a" and stat.ttot == 45:
                fsa = stat
                break
        self.assertTrue(fsa is not None)
        
        self.assertEqual(fsa.ncall, 7)
        self.assertEqual(fsa.nactualcall, 3)
        self.assertEqual(fsa.ttot, 45)
        self.assertEqual(fsa.tsub, 10)
        fsb = utils.find_stat_by_name(stats, "b")
        fsc = utils.find_stat_by_name(stats, "c")
        self.assertEqual(fsb.ncall, 6)
        self.assertEqual(fsb.nactualcall, 3)
        self.assertEqual(fsb.ttot, 36)
        self.assertEqual(fsb.tsub, 27)
        self.assertEqual(fsb.tavg, 6)
        self.assertEqual(fsc.ttot, 8)
        self.assertEqual(fsc.tsub, 8)
        self.assertEqual(fsc.tavg, 4)
        self.assertEqual(fsc.nactualcall, fsc.ncall, 2)
"""        
    
"""  
class MultithreadedScenarios(utils.YappiUnitTestCase):
    def test_subsequent_profile(self):
        WORKER_COUNT = 5
        def a(): pass
        def b(): pass
        def c(): pass
        
        _timings = {"a_1":3,"b_1":2,"c_1":1,}
        
        yappi.start()
        def g(): pass
        g()
        yappi.stop()
        yappi.clear_stats()
        _yappi._set_test_timings(_timings)
        yappi.start()
        
        _dummy = []
        for i in range(WORKER_COUNT):
            t = threading.Thread(target=a)
            t.start()
            t.join()
        for i in range(WORKER_COUNT):
            t = threading.Thread(target=b)
            t.start()
            _dummy.append(t)
            t.join()
        for i in range(WORKER_COUNT):
            t = threading.Thread(target=a)
            t.start()
            t.join()
        for i in range(WORKER_COUNT):
            t = threading.Thread(target=c)
            t.start()
            t.join()    
        yappi.stop()    
        yappi.start()
        def f():
            pass
        f() 
        stats = yappi.get_func_stats()
        fsa = utils.find_stat_by_name(stats, 'a')
        fsb = utils.find_stat_by_name(stats, 'b')
        fsc = utils.find_stat_by_name(stats, 'c')
        self.assertEqual(fsa.ncall, 10)
        self.assertEqual(fsb.ncall, 5)
        self.assertEqual(fsc.ncall, 5)
        self.assertEqual(fsa.ttot, fsa.tsub, 30)
        self.assertEqual(fsb.ttot, fsb.tsub, 10)
        self.assertEqual(fsc.ttot, fsc.tsub, 5)
        
        # MACOSx optimizes by only creating one worker thread
        self.assertTrue(len(yappi.get_thread_stats()) >= 2) 
           
    def test_basic(self):
        yappi.set_clock_type('wall')
        def dummy():
            pass
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
        fsa1 = utils.find_stat_by_name(stats, 'Worker1.a')
        fsa2 = utils.find_stat_by_name(stats, 'a')
        self.assertTrue(fsa1 is not None)
        self.assertTrue(fsa2 is not None)
        self.assertTrue(fsa1.ttot > 0.2)
        self.assertTrue(fsa2.ttot > 0.1)
        tstats = yappi.get_thread_stats()
        self.assertEqual(len(tstats), 2)
        tsa = utils.find_stat_by_name(tstats, 'Worker1')
        tsm = utils.find_stat_by_name(tstats, '_MainThread')
        dummy() # call dummy to force ctx name to be retrieved again.
        self.assertTrue(tsa is not None)
        # TODO: I put dummy() to fix below, remove the comments after a while.
        self.assertTrue( # FIX: I see this fails sometimes?
            tsm is not None, 
            'Could not find "_MainThread". Found: %s' % (', '.join(utils.get_stat_names(tstats)))) 
        
    def test_ctx_stats(self):
        from threading import Thread
        DUMMY_WORKER_COUNT = 5
        yappi.start()
        class DummyThread(Thread): pass
        
        def dummy():
            pass

        def dummy_worker():
            pass
        for i in range(DUMMY_WORKER_COUNT):
            t = DummyThread(target=dummy_worker)
            t.start()
            t.join()
        yappi.stop()
        stats = yappi.get_thread_stats()
        tsa = utils.find_stat_by_name(stats, "DummyThread")
        self.assertTrue(tsa is not None)
        yappi.clear_stats()
        time.sleep(1.0)
        _timings = {"a_1":6,"b_1":5,"c_1":3, "d_1":1, "a_2":4,"b_2":3,"c_2":2, "d_2":1}
        _yappi._set_test_timings(_timings)
        class Thread1(Thread): pass
        class Thread2(Thread): pass
        def a():
            b()
        def b():
            c()
        def c():
            d()
        def d():
            time.sleep(0.6)
        yappi.set_clock_type("wall")
        yappi.start()
        t1 = Thread1(target=a)
        t1.start()
        t2 = Thread2(target=a)
        t2.start()
        t1.join()
        t2.join()        
        stats = yappi.get_thread_stats()
        
        # the fist clear_stats clears the context table?
        tsa = utils.find_stat_by_name(stats, "DummyThread") 
        self.assertTrue(tsa is None)
        
        tst1 = utils.find_stat_by_name(stats, "Thread1")
        tst2 = utils.find_stat_by_name(stats, "Thread2")
        tsmain = utils.find_stat_by_name(stats, "_MainThread")
        dummy() # call dummy to force ctx name to be retrieved again.
        self.assertTrue(len(stats) == 3)
        self.assertTrue(tst1 is not None)
        self.assertTrue(tst2 is not None)
        # TODO: I put dummy() to fix below, remove the comments after a while.
        self.assertTrue( # FIX: I see this fails sometimes
            tsmain is not None,
            'Could not find "_MainThread". Found: %s' % (', '.join(utils.get_stat_names(stats))))
        self.assertTrue(1.0 > tst2.ttot >= 0.5)
        self.assertTrue(1.0 > tst1.ttot >= 0.5)
        
        # test sorting of the ctx stats
        stats = stats.sort("totaltime", "desc")
        prev_stat = None
        for stat in stats:
            if prev_stat:
                self.assertTrue(prev_stat.ttot >= stat.ttot)
            prev_stat = stat
        stats = stats.sort("totaltime", "asc")
        prev_stat = None
        for stat in stats:
            if prev_stat:
                self.assertTrue(prev_stat.ttot <= stat.ttot)
            prev_stat = stat
        stats = stats.sort("schedcount", "desc")
        prev_stat = None
        for stat in stats:
            if prev_stat:
                self.assertTrue(prev_stat.sched_count >= stat.sched_count)
            prev_stat = stat
        stats = stats.sort("name", "desc")
        prev_stat = None
        for stat in stats:
            if prev_stat:
                self.assertTrue(prev_stat.name >= stat.name)
            prev_stat = stat
        self.assertRaises(yappi.YappiError, stats.sort, "invalid_thread_sorttype_arg")
        self.assertRaises(yappi.YappiError, stats.sort, "invalid_thread_sortorder_arg")
        
    def test_producer_consumer_with_queues(self):
        # we currently just stress yappi, no functionality test is done here.
        yappi.start()
        if utils.is_py3x():
            from queue import Queue
        else:
            from Queue import Queue
        from threading import Thread
        WORKER_THREAD_COUNT = 50
        WORK_ITEM_COUNT = 2000
        def worker():
            while True:
                item = q.get()                
                # do the work with item
                q.task_done()

        q = Queue()
        for i in range(WORKER_THREAD_COUNT):
            t = Thread(target=worker)
            t.daemon = True
            t.start()
             
        for item in range(WORK_ITEM_COUNT):
            q.put(item)
        q.join()# block until all tasks are done
        #yappi.get_func_stats().sort("callcount").print_all()
        yappi.stop()
     
    def test_temporary_lock_waiting(self):
        yappi.start()
        _lock = threading.Lock()
        def worker():
            _lock.acquire()
            try:
                time.sleep(1.0)
            finally:
                _lock.release()
        t1 = threading.Thread(target=worker)
        t2 = threading.Thread(target=worker)
        t1.start()
        t2.start()
        t1.join()
        t2.join()
        #yappi.get_func_stats().sort("callcount").print_all()
        yappi.stop()
    
    @_unittest.skipIf(os.name != "posix", "requires Posix compliant OS")
    def test_signals_with_blocking_calls(self): 
        import signal, os, time 
        # just to verify if signal is handled correctly and stats/yappi are not corrupted.
        def handler(signum, frame): 
            raise Exception("Signal handler executed!")
        yappi.start()    
        signal.signal(signal.SIGALRM, handler) 
        signal.alarm(1)
        self.assertRaises(Exception, time.sleep, 2)
        stats = yappi.get_func_stats()
        fsh = utils.find_stat_by_name(stats, "handler")
        self.assertTrue(fsh is not None)
           
    @_unittest.skipIf(not sys.version_info >= (3, 2), "requires Python 3.2")
    def test_concurrent_futures(self):
        yappi.start()
        from concurrent.futures import ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=5) as executor:
            f = executor.submit(pow, 5, 2)
            self.assertEqual(f.result(), 25)        
        time.sleep(1.0)
        yappi.stop()
        
    @_unittest.skipIf(not sys.version_info >= (3, 2), "requires Python 3.2")
    def test_barrier(self):
        yappi.start()
        b = threading.Barrier(2, timeout=1)
        def worker():
            try:
                b.wait()
            except threading.BrokenBarrierError:
                pass
            except Exception:
                raise Exception("BrokenBarrierError not raised")
        t1 = threading.Thread(target=worker)
        t1.start()
        #b.wait()
        t1.join()
        yappi.stop()
    
class NonRecursiveFunctions(utils.YappiUnitTestCase):
    def test_abcd(self):
        _timings = {"a_1":6,"b_1":5,"c_1":3, "d_1":1}
        _yappi._set_test_timings(_timings)

        def a():
            b()
        def b():
            c()
        def c():
            d()
        def d():
            pass
        stats = utils.run_and_get_func_stats(a)
        fsa = utils.find_stat_by_name(stats, 'a')
        fsb = utils.find_stat_by_name(stats, 'b')
        fsc = utils.find_stat_by_name(stats, 'c')
        fsd = utils.find_stat_by_name(stats, 'd')
        cfsab = fsa.children[fsb]
        cfsbc = fsb.children[fsc]
        cfscd = fsc.children[fsd]

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
        _timings = {"a_1":6,"b_1":4}
        _yappi._set_test_timings(_timings)

        def a():
            b()
            yappi.stop()
            
        def b():    
            time.sleep(0.2)

        yappi.start()
        a()
        stats = yappi.get_func_stats()
        fsa = utils.find_stat_by_name(stats, 'a')
        fsb = utils.find_stat_by_name(stats, 'b')

        self.assertEqual(fsa.ncall , 1)
        self.assertEqual(fsa.nactualcall, 0)
        self.assertEqual(fsa.ttot , 0) # no call_leave called
        self.assertEqual(fsa.tsub , 0) # no call_leave called
        self.assertEqual(fsb.ttot , 4) 
        
class RecursiveFunctions(utils.YappiUnitTestCase): 
    def test_fibonacci(self):
        def fib(n):
           if n > 1:
               return fib(n-1) + fib(n-2)
           else:
               return n
        stats = utils.run_and_get_func_stats(fib, 22)
        fs = utils.find_stat_by_name(stats, 'fib')
        self.assertEqual(fs.ncall, 57313)
        self.assertEqual(fs.ttot, fs.tsub)
        
    def test_abcadc(self):
        _timings = {"a_1":20,"b_1":19,"c_1":17, "a_2":13, "d_1":12, "c_2":10, "a_3":5}
        _yappi._set_test_timings(_timings)
            
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
        stats = utils.run_and_get_func_stats(a, 1)
        fsa = utils.find_stat_by_name(stats, 'a')
        fsb = utils.find_stat_by_name(stats, 'b')
        fsc = utils.find_stat_by_name(stats, 'c')
        fsd = utils.find_stat_by_name(stats, 'd')
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
        cfsca = fsc.children[fsa]
        self.assertEqual(cfsca.nactualcall, 0)
        self.assertEqual(cfsca.ncall, 2)
        self.assertEqual(cfsca.ttot, 13)
        self.assertEqual(cfsca.tsub, 6)
        
    def test_aaaa(self):
        _timings = {"d_1":9, "d_2":7, "d_3":3, "d_4":2}
        _yappi._set_test_timings(_timings)
        def d(n):
            if n == 3:
                return
            d(n+1)
        stats = utils.run_and_get_func_stats(d, 0)
        fsd = utils.find_stat_by_name(stats, 'd')
        self.assertEqual(fsd.ncall , 4)
        self.assertEqual(fsd.nactualcall , 1)
        self.assertEqual(fsd.ttot , 9)
        self.assertEqual(fsd.tsub , 9)
        cfsdd = fsd.children[fsd]
        self.assertEqual(cfsdd.ttot , 7)
        self.assertEqual(cfsdd.tsub , 7)
        self.assertEqual(cfsdd.ncall , 3)
        self.assertEqual(cfsdd.nactualcall , 0)
        
    def test_abcabc(self):
        _timings = {"a_1":20,"b_1":19,"c_1":17, "a_2":13, "b_2":11, "c_2":9, "a_3":6}
        _yappi._set_test_timings(_timings)
            
        def a(n):
            if n == 3:
                return
            else:
                b(n)
        def b(n):        
            c(n)    
        def c(n):
            a(n+1)    

        stats = utils.run_and_get_func_stats(a, 1)
        fsa = utils.find_stat_by_name(stats, 'a')
        fsb = utils.find_stat_by_name(stats, 'b')
        fsc = utils.find_stat_by_name(stats, 'c')
        self.assertEqual(fsa.ncall , 3)
        self.assertEqual(fsa.nactualcall , 1)
        self.assertEqual(fsa.ttot , 20)
        self.assertEqual(fsa.tsub , 9)
        self.assertEqual(fsb.ttot , 19)
        self.assertEqual(fsb.tsub , 4)
        self.assertEqual(fsc.ttot , 17)
        self.assertEqual(fsc.tsub , 7)
        cfsab = fsa.children[fsb]
        cfsbc = fsb.children[fsc]
        cfsca = fsc.children[fsa]
        self.assertEqual(cfsab.ttot , 19)
        self.assertEqual(cfsab.tsub , 4)
        self.assertEqual(cfsbc.ttot , 17)
        self.assertEqual(cfsbc.tsub , 7)
        self.assertEqual(cfsca.ttot , 13)
        self.assertEqual(cfsca.tsub , 8)
        
    def test_abcbca(self):
        _timings = {"a_1":10,"b_1":9,"c_1":7,"b_2":4,"c_2":2,"a_2":1}
        _yappi._set_test_timings(_timings)
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
        stats = utils.run_and_get_func_stats(a)
        fsa = utils.find_stat_by_name(stats, 'a')
        fsb = utils.find_stat_by_name(stats, 'b')
        fsc = utils.find_stat_by_name(stats, 'c')
        cfsab = fsa.children[fsb]
        cfsbc = fsb.children[fsc]
        cfsca = fsc.children[fsa]
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
        _yappi._set_test_timings(_timings)
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
                
        stats = utils.run_and_get_func_stats(a)
        fsa = utils.find_stat_by_name(stats, 'a')
        fsb = utils.find_stat_by_name(stats, 'b')
        fsc = utils.find_stat_by_name(stats, 'c')
        cfsaa = fsa.children[fsa.index]
        cfsab = fsa.children[fsb]
        cfsbc = fsb.children[fsc.full_name]
        cfscc = fsc.children[fsc]
        cfscb = fsc.children[fsb]
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
        _yappi._set_test_timings(_timings)

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
            
        stats = utils.run_and_get_func_stats(a)
        fsa = utils.find_stat_by_name(stats, 'a')
        fsb = utils.find_stat_by_name(stats, 'b')
        cfsaa = fsa.children[fsa]
        cfsba = fsb.children[fsa]
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
        _yappi._set_test_timings(_timings)

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
            
        stats = utils.run_and_get_func_stats(a)
        fsa = utils.find_stat_by_name(stats, 'a')
        fsb = utils.find_stat_by_name(stats, 'b')
        cfsaa = fsa.children[fsa]
        cfsab = fsa.children[fsb]
        cfsbb = fsb.children[fsb]
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
        _yappi._set_test_timings(_timings)

        self._ncall = 1
        def a():
            if self._ncall == 1:
                b()
        def b():
            if self._ncall == 3:
                return
            self._ncall += 1
            b()
            
        stats = utils.run_and_get_func_stats(a)
        fsa = utils.find_stat_by_name(stats, 'a')
        fsb = utils.find_stat_by_name(stats, 'b')
        cfsab = fsa.children[fsb]
        cfsbb = fsb.children[fsb]
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
        _yappi._set_test_timings(_timings)

        self._ncall = 1
        def a():
            if self._ncall == 3:
                b()
                return
            self._ncall += 1
            a()
        def b():
            return
            
        stats = utils.run_and_get_func_stats(a)
        fsa = utils.find_stat_by_name(stats, 'a')
        fsb = utils.find_stat_by_name(stats, 'b')
        cfsaa = fsa.children[fsa]
        cfsab = fsa.children[fsb]
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
        _yappi._set_test_timings(_timings)

        self._ncall = 1
        def a():
            b()
        def b():
            if self._ncall == 2:
                return
            self._ncall += 1
            a()
            
        stats = utils.run_and_get_func_stats(a)
        fsa = utils.find_stat_by_name(stats, 'a')
        fsb = utils.find_stat_by_name(stats, 'b')
        cfsab = fsa.children[fsb]
        cfsba = fsb.children[fsa]
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


if __name__ == '__main__':
#     import sys;sys.argv = ['', 'BasicUsage.test_run_as_script']
#     import sys;sys.argv = ['', 'MultithreadedScenarios.test_subsequent_profile']
    _unittest.main()
