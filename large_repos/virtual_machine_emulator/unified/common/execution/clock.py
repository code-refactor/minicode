"""Global clock management for synchronized execution."""

from typing import List, Callable, Optional


class GlobalClock:
    """Global clock for VM synchronization."""
    
    def __init__(self):
        """Initialize global clock."""
        self.current_cycle = 0
        self.subscribers: List[Callable[[int], None]] = []
        self.paused = False
        
    def tick(self) -> int:
        """Advance clock by one cycle."""
        if not self.paused:
            self.current_cycle += 1
            self._notify_subscribers()
        return self.current_cycle
    
    def advance(self, cycles: int) -> int:
        """Advance clock by multiple cycles."""
        if not self.paused and cycles > 0:
            for _ in range(cycles):
                self.tick()
        return self.current_cycle
    
    def get_cycle(self) -> int:
        """Get current cycle count."""
        return self.current_cycle
    
    def reset(self) -> None:
        """Reset clock to zero."""
        self.current_cycle = 0
        self._notify_subscribers()
    
    def pause(self) -> None:
        """Pause the clock."""
        self.paused = True
    
    def resume(self) -> None:
        """Resume the clock."""
        self.paused = False
    
    def subscribe(self, callback: Callable[[int], None]) -> None:
        """Subscribe to clock updates."""
        if callback not in self.subscribers:
            self.subscribers.append(callback)
    
    def unsubscribe(self, callback: Callable[[int], None]) -> None:
        """Unsubscribe from clock updates."""
        if callback in self.subscribers:
            self.subscribers.remove(callback)
    
    def _notify_subscribers(self) -> None:
        """Notify all subscribers of clock update."""
        for callback in self.subscribers:
            try:
                callback(self.current_cycle)
            except Exception:
                # Ignore errors in subscribers
                pass
    
    def __repr__(self) -> str:
        """String representation."""
        status = "paused" if self.paused else "running"
        return f"GlobalClock(cycle={self.current_cycle}, {status})"


class CycleTimer:
    """Timer for measuring cycle intervals."""
    
    def __init__(self, clock: GlobalClock):
        """Initialize timer with clock reference."""
        self.clock = clock
        self.start_cycle: Optional[int] = None
        self.elapsed_cycles: int = 0
        
    def start(self) -> None:
        """Start the timer."""
        self.start_cycle = self.clock.get_cycle()
        self.elapsed_cycles = 0
    
    def stop(self) -> int:
        """Stop the timer and return elapsed cycles."""
        if self.start_cycle is not None:
            self.elapsed_cycles = self.clock.get_cycle() - self.start_cycle
            self.start_cycle = None
        return self.elapsed_cycles
    
    def get_elapsed(self) -> int:
        """Get elapsed cycles without stopping."""
        if self.start_cycle is not None:
            return self.clock.get_cycle() - self.start_cycle
        return self.elapsed_cycles
    
    def reset(self) -> None:
        """Reset the timer."""
        self.start_cycle = None
        self.elapsed_cycles = 0