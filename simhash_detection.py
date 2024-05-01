def simple_hash(value, hash_bits=64):
    hash_value = 0
    for i, char in enumerate(value):
        hash_value += (ord(char) << i)
    hash_value = hash_value % (1 << hash_bits)
    return hash_value

def simhash(features, hash_bits=64):
    v = [0] * hash_bits
    for feature, weight in features.items():
        hash_value = simple_hash(feature, hash_bits)
        for i in range(hash_bits):
            bitmask = 1 << i
            if hash_value & bitmask:
                v[i] += weight
            else:
                v[i] -= weight
    fingerprint = 0
    for i in range(hash_bits):
        if v[i] > 0:
            fingerprint |= (1 << i)

    return fingerprint

def hamming_distance(hash1, hash2):
    x = hash1 ^ hash2
    distance = 0
    while x:
        distance += 1
        x &= x - 1 
    return distance

def calculate_features(text):
    words = text.split()
    weights = {}
    for word in words:
        weights[word] = weights.get(word, 0) + 1
    return weights


simhashes = {}
def page_content(url, content):
    features = calculate_features(content)
    page_simhash = simhash(features)
    simhashes[url] = page_simhash
    return page_simhash

def detect_near_duplicates(url, new_simhash):
    threshold = 5  # Define your similarity threshold
    for existing_url, existing_simhash in simhashes.items():
        if hamming_distance(new_simhash, existing_simhash) < threshold:
            simhashes[url] = new_simhash
            return True
    simhashes[url] = new_simhash
    return False
