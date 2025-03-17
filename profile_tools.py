import cProfile
import pstats
import time
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from io import StringIO
import argparse
import os
import random
from joblib import Parallel, delayed

def profile_feature_extraction(dbname, lat, lon, db_host="172.18.0.2", db_port="5432"):
    """
    Profile the feature extraction for a single point.
    
    This function helps identify the most time-consuming queries.
    """
    from OSM_featureExtraction import OSMRequestor
    
    profiler = cProfile.Profile()
    profiler.enable()
    
    # Create a requestor and extract features
    requestor = OSMRequestor.Requestor(dbname, db_host, db_port)
    features = requestor.create_features(lon, lat)
    requestor.close()
    
    profiler.disable()
    
    # Output profiling results
    s = StringIO()
    ps = pstats.Stats(profiler, stream=s).sort_stats('cumulative')
    ps.print_stats(20)  # Show top 20 function calls
    
    print(s.getvalue())
    
    # Save detailed profiling data
    profiler.dump_stats(f"feature_extraction_profile_{lat}_{lon}.prof")
    
    return features

def compare_query_approaches(dbname, lat, lon, db_host="172.18.0.2", db_port="5432"):
    """
    Compare different query approaches and their performance.
    """
    from OSM_featureExtraction import OSMRequestor
    
    # Original approach with full range
    requestor1 = OSMRequestor.Requestor(dbname, db_host, db_port)
    
    # Test with original full range (50-3050 by 50)
    start_time = time.time()
    full_range_radii = list(range(50, 3050, 50))
    commercial_full = requestor1.query_osm_polygone(lon, lat, full_range_radii, "landuse", "commercial")
    full_range_time = time.time() - start_time
    
    # Test with reduced range (7 strategic points)
    start_time = time.time()
    reduced_range_radii = [50, 100, 200, 400, 800, 1600, 3000]
    commercial_reduced = requestor1.query_osm_polygone(lon, lat, reduced_range_radii, "landuse", "commercial")
    reduced_range_time = time.time() - start_time
    
    requestor1.close()
    
    # Print comparison
    print(f"Query performance comparison:")
    print(f"  - Full range (60 points): {full_range_time:.4f} seconds")
    print(f"  - Reduced range (7 points): {reduced_range_time:.4f} seconds")
    print(f"  - Speedup: {full_range_time/reduced_range_time:.2f}x")
    
    # Compare data quality (values at specific points)
    common_points = [50, 100, 3000]  # Points that exist in both datasets
    
    comparison_data = {
        'radius': common_points,
        'full_range': [commercial_full.get(f"commercial_{r}m", 0) for r in common_points],
        'reduced_range': [commercial_reduced.get(f"commercial_{r}m", 0) for r in common_points]
    }
    
    comparison_df = pd.DataFrame(comparison_data)
    print("\nData quality comparison at sample points:")
    print(comparison_df)
    
    return {
        'full_range_time': full_range_time,
        'reduced_range_time': reduced_range_time,
        'comparison_data': comparison_df
    }

def batch_test_performance(dbname, points, db_host="172.18.0.2", db_port="5432"):
    """
    Test performance across multiple points to ensure consistency.
    
    Args:
        dbname: Database name
        points: List of (lat, lon) tuples to test
    """
    from OSM_featureExtraction import OSMRequestor
    
    # Initialize results storage
    results = {
        'original': [],
        'optimized': []
    }
    
    # Test each point
    for i, (lat, lon) in enumerate(points):
        print(f"Testing point {i+1}/{len(points)}: ({lat}, {lon})")
        
        # Test original approach
        requestor = OSMRequestor.Requestor(dbname, db_host, db_port)
        start_time = time.time()
        
        # Simulate the original create_features with full ranges
        full_range_radii = list(range(50, 3050, 50))
        road_range_radii = list(range(50, 1550, 50))
        
        _ = requestor.query_osm_polygone(lon, lat, full_range_radii, "landuse", "commercial")
        _ = requestor.query_osm_polygone(lon, lat, full_range_radii, "landuse", "residential")
        _ = requestor.query_osm_highway(lon, lat, road_range_radii)
        
        original_time = time.time() - start_time
        results['original'].append(original_time)
        
        # Test optimized approach
        start_time = time.time()
        
        # Simulate the optimized create_features with reduced ranges
        reduced_range_radii = [50, 100, 200, 400, 800, 1600, 3000]
        reduced_road_range = [50, 100, 200, 400, 800, 1500]
        
        _ = requestor.query_osm_polygone(lon, lat, reduced_range_radii, "landuse", "commercial")
        _ = requestor.query_osm_polygone(lon, lat, reduced_range_radii, "landuse", "residential")
        _ = requestor.query_osm_highway(lon, lat, reduced_road_range)
        
        optimized_time = time.time() - start_time
        results['optimized'].append(optimized_time)
        
        requestor.close()
    
    # Summarize results
    original_avg = np.mean(results['original'])
    optimized_avg = np.mean(results['optimized'])
    
    print(f"\nPerformance summary across {len(points)} points:")
    print(f"  - Original approach: {original_avg:.4f} seconds (avg)")
    print(f"  - Optimized approach: {optimized_avg:.4f} seconds (avg)")
    print(f"  - Average speedup: {original_avg/optimized_avg:.2f}x")
    
    return results

def profile_region(dbname, latmin, latmax, lonmin, lonmax, n_samples=10, n_workers=1, db_host="172.18.0.2", db_port="5432"):
    """
    Profile feature extraction across a region by sampling random points.
    
    Args:
        dbname: Database name
        latmin, latmax, lonmin, lonmax: Region boundaries
        n_samples: Number of random points to sample within the region
        n_workers: Number of parallel workers
    """
    print(f"Profiling region: lat [{latmin}, {latmax}], lon [{lonmin}, {lonmax}]")
    print(f"Sampling {n_samples} random points within the region")
    
    # Generate random sampling points within the region
    random.seed(42)  # For reproducibility
    sample_points = []
    for _ in range(n_samples):
        lat = latmin + random.random() * (latmax - latmin)
        lon = lonmin + random.random() * (lonmax - lonmin)
        sample_points.append((lat, lon))
    
    # Run batch performance test on these sample points
    results = batch_test_performance(dbname, sample_points, db_host, db_port)
    
    # Visualize the results
    visualize_performance(results)
    
    # Estimate full region performance
    # Calculate approximate grid size
    grid_size = int((latmax - latmin) * (lonmax - lonmin) / 0.001 / 0.001)  # Assuming 0.001 degree granularity
    
    print(f"\nEstimated performance for full region ({grid_size} grid points):")
    print(f"  - Original approach: {grid_size * np.mean(results['original']) / 3600:.2f} hours")
    print(f"  - Optimized approach: {grid_size * np.mean(results['optimized']) / 3600:.2f} hours")
    print(f"  - Estimated time saved: {grid_size * (np.mean(results['original']) - np.mean(results['optimized'])) / 3600:.2f} hours")
    
    return results

def compare_parallel_performance(dbname, latmin, latmax, lonmin, lonmax, workers_list=[1, 2, 4, 8], db_host="172.18.0.2", db_port="5432"):
    """
    Compare performance with different numbers of workers on a small region.
    
    Args:
        dbname: Database name
        latmin, latmax, lonmin, lonmax: Region boundaries
        workers_list: List of worker counts to test
    """
    from OSM_featureExtraction.FeatureGenerator import FeatureGenerator
    import numpy as np
    
    print(f"Testing parallel performance on region: lat [{latmin}, {latmax}], lon [{lonmin}, {lonmax}]")
    
    # Define a small test region (1/10th of the provided region in each dimension)
    test_latmin = latmin
    test_latmax = latmin + (latmax - latmin) / 10
    test_lonmin = lonmin
    test_lonmax = lonmin + (lonmax - lonmin) / 10
    
    performance_results = []
    
    # Test with different worker counts
    for n_workers in workers_list:
        print(f"\nTesting with {n_workers} workers...")
        
        # Create feature generator
        fg = FeatureGenerator(dbname, db_host=db_host, db_port=db_port)
        
        # Generate grid points for the test region
        fg.generateMap(test_latmin, test_latmax, test_lonmin, test_lonmax, granularity=0.002)
        
        # Process features with timing
        start_time = time.time()
        fg.preproc_landuse_features_parallel(n_workers)
        end_time = time.time()
        
        processing_time = end_time - start_time
        points_per_second = len(fg.data) / processing_time
        
        performance_results.append({
            'workers': n_workers,
            'time': processing_time,
            'points': len(fg.data),
            'points_per_second': points_per_second
        })
        
        print(f"  - Processed {len(fg.data)} points in {processing_time:.2f} seconds")
        print(f"  - Rate: {points_per_second:.2f} points/second")
    
    # Visualize parallel performance
    df = pd.DataFrame(performance_results)
    
    plt.figure(figsize=(10, 6))
    plt.bar(df['workers'].astype(str), df['points_per_second'])
    plt.xlabel('Number of Workers')
    plt.ylabel('Points Processed per Second')
    plt.title('Parallel Processing Performance')
    
    for i, v in enumerate(df['points_per_second']):
        plt.text(i, v + 0.5, f"{v:.2f}", ha='center')
    
    plt.tight_layout()
    plt.savefig('parallel_performance.png')
    plt.close()
    
    # Calculate and print speedup relative to single worker
    baseline = df.loc[df['workers'] == 1, 'points_per_second'].values[0]
    df['speedup'] = df['points_per_second'] / baseline
    
    print("\nParallel Processing Speedup:")
    print(df[['workers', 'points_per_second', 'speedup']])
    
    return df

def visualize_performance(results):
    """
    Create a bar chart comparing original vs optimized performance.
    """
    labels = ['Original', 'Optimized']
    values = [np.mean(results['original']), np.mean(results['optimized'])]
    
    plt.figure(figsize=(10, 6))
    plt.bar(labels, values, color=['#ff9999', '#66b3ff'])
    plt.ylabel('Average Time (seconds)')
    plt.title('Query Performance Comparison')
    
    # Add labels on top of bars
    for i, v in enumerate(values):
        plt.text(i, v + 0.01, f"{v:.4f}s", ha='center')
    
    # Add speedup label
    speedup = values[0] / values[1]
    plt.text(0.5, max(values) * 0.5, f"{speedup:.2f}x speedup", 
             ha='center', fontsize=14, bbox=dict(facecolor='white', alpha=0.8))
    
    plt.tight_layout()
    plt.savefig('performance_comparison.png')
    plt.close()
    
    # Create individual point comparison
    plt.figure(figsize=(12, 6))
    
    x = np.arange(len(results['original']))
    width = 0.35
    
    plt.bar(x - width/2, results['original'], width, label='Original')
    plt.bar(x + width/2, results['optimized'], width, label='Optimized')
    
    plt.xlabel('Test Point')
    plt.ylabel('Time (seconds)')
    plt.title('Performance Comparison by Test Point')
    plt.legend()
    plt.tight_layout()
    plt.savefig('performance_by_point.png')
    plt.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Profile and test OpenLUR query optimizations")
    parser.add_argument("dbname", help="Database name to connect to")
    parser.add_argument("--host", default="172.18.0.2", help="Database host")
    parser.add_argument("--port", default="5432", help="Database port")
    
    # Single point profiling options
    parser.add_argument("--lat", type=float, help="Latitude for single point test")
    parser.add_argument("--lon", type=float, help="Longitude for single point test")
    
    # Batch testing options
    parser.add_argument("--batch", action="store_true", help="Run batch testing")
    
    # Region profiling options
    parser.add_argument("--region", action="store_true", help="Profile a region")
    parser.add_argument("--latmin", type=float, help="Minimum latitude of region")
    parser.add_argument("--latmax", type=float, help="Maximum latitude of region")
    parser.add_argument("--lonmin", type=float, help="Minimum longitude of region")
    parser.add_argument("--lonmax", type=float, help="Maximum longitude of region")
    parser.add_argument("--samples", type=int, default=10, help="Number of sample points in region")
    
    # Parallel performance testing
    parser.add_argument("--parallel", action="store_true", help="Test parallel performance")
    parser.add_argument("--workers", type=str, default="1,2,4,8", help="Comma-separated list of worker counts to test")
    
    args = parser.parse_args()
    
    if args.lat and args.lon:
        # Run single point profiling
        print(f"Profiling feature extraction at ({args.lat}, {args.lon})...")
        profile_feature_extraction(args.dbname, args.lat, args.lon, args.host, args.port)
        
        # Compare query approaches
        print("\nComparing query approaches...")
        comparison = compare_query_approaches(args.dbname, args.lat, args.lon, args.host, args.port)
    
    if args.batch:
        # Define test points (example - adjust as needed)
        test_points = [
            (args.lat, args.lon),  # Use provided point as first test
            (args.lat + 0.01, args.lon),
            (args.lat, args.lon + 0.01),
            (args.lat - 0.01, args.lon),
            (args.lat, args.lon - 0.01)
        ]
        
        print("\nRunning batch performance test...")
        results = batch_test_performance(args.dbname, test_points, args.host, args.port)
        
        # Create visualizations
        visualize_performance(results)
    
    if args.region:
        if not all([args.latmin, args.latmax, args.lonmin, args.lonmax]):
            print("Error: Region profiling requires --latmin, --latmax, --lonmin, and --lonmax")
            exit(1)
            
        # Profile region
        profile_region(args.dbname, args.latmin, args.latmax, args.lonmin, args.lonmax, 
                      args.samples, 1, args.host, args.port)
    
    if args.parallel:
        if not all([args.latmin, args.latmax, args.lonmin, args.lonmax]):
            print("Error: Parallel testing requires --latmin, --latmax, --lonmin, and --lonmax")
            exit(1)
            
        # Parse worker counts
        workers_list = [int(w) for w in args.workers.split(',')]
        
        # Test parallel performance
        compare_parallel_performance(args.dbname, args.latmin, args.latmax, args.lonmin, args.lonmax,
                                    workers_list, args.host, args.port)