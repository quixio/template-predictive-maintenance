import dask.array as da

# Create a large array filled with random numbers
x = da.random.random((1000000, 1000000), chunks=(1000000, 1000000))

# Perform some computation on the array
y = x + x.T
z = y.mean(axis=0)

# Compute the result in parallel
result = z.compute()