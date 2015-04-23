from marisa_trie import BytesTrie
keys = [u'foo', u'bar', u'foobar', u'foo']
values = [b'foo-value', b'bar-value', b'foobar-value', b'foo-value2']
trie = BytesTrie(zip(keys, values))
print trie[u'bar']
trie.save('benchmark.bytes_trie')

trie = BytesTrie()
trie.mmap('benchmark.bytes_trie')
print trie.get(u'bar')
