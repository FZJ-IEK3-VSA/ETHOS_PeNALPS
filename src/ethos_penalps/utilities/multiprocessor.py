# from multiprocessing import Process, Queue


# class Multiprocessor:

#     def __init__(self):
#         self.processes = []
#         self.queue = Queue()

#     @staticmethod
#     def _wrapper(func, queue, args, kwargs):
#         ret = func(*args, **kwargs)
#         queue.put(ret)

#     def run(self, func, *args, **kwargs):
#         args2 = [func, self.queue, args, kwargs]
#         p = Process(target=self._wrapper, args=args2)
#         self.processes.append(p)
#         p.start()

#     def wait(self):
#         rets = []
#         for p in self.processes:
#             ret = self.queue.get()
#             rets.append(ret)
#         for p in self.processes:
#             p.join()
#         return rets


# from multiprocessing import Process, Manager


# class Multiprocessor:
#     def __init__(self):
#         self.processes = []
#         self.manager: Manager = Manager()
#         self.queue = self.manager.Queue()

#     @staticmethod
#     def _wrapper(func, queue, args, kwargs):
#         ret = func(*args, **kwargs)
#         queue.put(ret)

#     def run(self, func, *args, **kwargs):
#         args2 = [func, self.queue, args, kwargs]
#         p = Process(target=self._wrapper, args=args2)
#         self.processes.append(p)
#         p.start()

#     def wait(self):
#         rets = []
#         for p in self.processes:
#             ret = self.queue.get()
#             rets.append(ret)
#         for p in self.processes:
#             p.join()
#         return rets

import multiprocessing
import multiprocessing.pool
from typing import Callable, Iterable


class AsynchronousMultiProcessor:
    def __init__(self, number_of_process: int | None) -> None:
        if number_of_process is None:
            number_of_process = int(multiprocessing.cpu_count() / 2)
        self.pool: multiprocessing.pool.Pool = multiprocessing.pool.Pool(processes=number_of_process)

    def run_function_in_parallel(self, func: Callable, iterable: Iterable):
        results = self.pool.map_async(func, iterable)
        results.wait()
        self.pool.close()
        self.pool.join()

        return results.get()
