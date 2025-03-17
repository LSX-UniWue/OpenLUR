import psycopg2
import psycopg2.pool
import threading
import time

class PgConnectionPool:
    """
    PostgreSQL connection pool for parallel processing.
    Provides thread-safe database connections.
    """
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls, *args, **kwargs):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(PgConnectionPool, cls).__new__(cls)
                cls._instance._initialized = False
            return cls._instance
    
    def __init__(self, dbname, host="172.18.0.2", port="5432", user="docker", password="docker", 
                 min_conn=5, max_conn=20):
        if self._initialized:
            return
            
        self.dbname = dbname
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.min_conn = min_conn
        self.max_conn = max_conn
        
        # Create connection pool
        self.pool = psycopg2.pool.ThreadedConnectionPool(
            min_conn, max_conn,
            dbname=dbname,
            user=user,
            password=password,
            host=host,
            port=port
        )
        
        # Track connections by thread
        self.thread_conns = {}
        self._lock = threading.Lock()
        self._initialized = True
        
        print(f"Initialized connection pool for {dbname} with {min_conn}-{max_conn} connections")
    
    def get_connection(self):
        """Get a connection from the pool, with thread tracking"""
        thread_id = threading.get_ident()
        
        with self._lock:
            if thread_id in self.thread_conns:
                # Return existing connection for this thread
                return self.thread_conns[thread_id]
                
            # Get new connection from pool
            try:
                conn = self.pool.getconn(key=thread_id)
                self.thread_conns[thread_id] = conn
                return conn
            except psycopg2.pool.PoolError as e:
                # Connection pool exhausted, retry after a short wait
                time.sleep(0.1)
                return self.get_connection()
    
    def return_connection(self, thread_id=None):
        """Return connection to the pool"""
        if thread_id is None:
            thread_id = threading.get_ident()
            
        with self._lock:
            if thread_id in self.thread_conns:
                conn = self.thread_conns[thread_id]
                del self.thread_conns[thread_id]
                self.pool.putconn(conn, key=thread_id)
    
    def close_all(self):
        """Close all connections and cleanup pool"""
        with self._lock:
            # Return all tracked connections
            for thread_id, conn in list(self.thread_conns.items()):
                self.pool.putconn(conn, key=thread_id)
                del self.thread_conns[thread_id]
            
            # Close the pool
            self.pool.closeall()
            print("Connection pool closed")
    
    @classmethod
    def get_pool(cls, dbname, host="172.18.0.2", port="5432", user="docker", password="docker", 
                min_conn=5, max_conn=20):
        """Get or create the connection pool instance"""
        if cls._instance is None or cls._instance.dbname != dbname:
            return cls(dbname, host, port, user, password, min_conn, max_conn)
        return cls._instance