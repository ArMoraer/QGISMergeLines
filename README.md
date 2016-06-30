MergeLines plugin
=================

Description
-----------

MergeLines is a simple plugin that merges elements of a line network (e.g. river network) in order to simplify its topology. The initial goal of this plugin was to "reconstruct" rivers and affluents when dealing with an oversegmented river network. The output layer has (in my tests) around half as lines as the input layer.

Polylines are ignored. Please split polylines into multiples lines if you want them to be treated, before using this plugin.

**Attributes:** the fields of the output layer are the same as the input layer. When two lines are merged, the resulting line has the same attributes as the longest merged line. More sophisticated approaches might be implemented in future versions, depending on requests.

Two merging methods are currently available :

* length: a line is merged with its longest neighbor;
* alignment: a line is merged with its best aligned neighbor (gives more "natural" results when dealing with a river network).

Difference with other plugins
-----------------------------

There already are 3 plugins that serve a similar, albeit different purpose : "Join lines", "Join multiples lines" and "Multiline join".

The main difference between the first two plugins and MergeLines is that MergeLines automatically merges features in a line layer, which proves useful when dealing with a large number of lines. In "Join lines" and "Join multiples lines", features have to be manually selected.

"Multiline join" deals with polylines. Its goal is to simplify polylines by merging parts a polyline together. MergeLines deals with networks of simple lines, and merges these lines according to various rules (which should become more complex in the near future).

UI
--

Input:

* Input layer: line vector layer;
* Merging method: *Length* or *Alignment* (see above).

Output:

* Output layer name: name of output layer (default = 'output').

Example
-------

Input layer (17 lines):

![Input layer](/img/demo_input.png "Input layer")

Output layer, 'Length' option (9 lines):

![Output layer](/img/demo_output_length.png "Output layer")

Output layer, 'Alignment' option (9 lines):

![Output layer](/img/demo_output_alignment.png "Output layer")
