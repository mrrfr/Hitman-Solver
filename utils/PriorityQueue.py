import heapq


class PriorityQueue:
    def __init__(self):
        self.Heap = []
        self.Count = 0

    def push(self, item, priority=0):
        entry = (priority, self.Count, item)
        heapq.heappush(self.Heap, entry)
        self.Count += 1

    def pop(self):
        (_, _, item) = heapq.heappop(self.Heap)
        return item

    def isEmpty(self):
        return len(self.Heap) == 0
