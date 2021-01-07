function setupGraph() {
  var radius = 7;
  var graph, layout, zoom, nodes, links, data;
  var linkedByIndex = {};
  var graphWidth, graphHeight;
  var centerFactor = 1;
  var durationInterval = 500;

  // helpers
  function formatClassName(prefix, object) {
    return prefix + '-' + object.id.replace(/[^_0-9a-zA-Z\-]/gi, '-');
  }

  function findElementByNode(prefix, node) {
    var selector = '.' + formatClassName(prefix, node);
    return graph.select(selector);
  }

  function isConnected(a, b) {
    return linkedByIndex[a.index + ',' + b.index] ||
      linkedByIndex[b.index + ',' + a.index] ||
      a.index == b.index;
  }

  function fadeRelatedNodes(dst, opacity, nodes, links) {
    // clean
    $('path.link').removeAttr('data-show');

    nodes.style('stroke-opacity', function (o) {
      if (isConnected(dst, o)) {
        var thisOpacity = 1;
      } else {
        var thisOpacity = opacity;
      }

      this.setAttribute('fill-opacity', thisOpacity);
      this.setAttribute('stroke-opacity', thisOpacity);

      if (thisOpacity == 1) {
        this.classList.remove('dimmed');
      } else {
        this.classList.add('dimmed');
      }

      return thisOpacity;
    });

    links.style('stroke-opacity', function (o) {
      var flag = false;

      if (o.target === dst) {
        // Highlight target/sources of the link
        var elmNodes = graph.selectAll('.' + formatClassName('node', o.source));
        elmNodes.attr('fill-opacity', 1);
        elmNodes.attr('stroke-opacity', 1);
        elmNodes.style('stroke-opacity', 1);

        elmNodes.classed('dimmed', false);

        // Highlight arrows
        var selector = 'path.link' +
          '[data-source=' + o.source.index + ']' +
          '[data-target=' + o.target.index + ']';
        var elmCurrentLink = $(selector);
        elmCurrentLink.attr('data-show', true);

        // In d3, the arrows are implemented as markers, and in SVG markers are
        // referenced using relative URLs. The base tag changes the default
        // links and breaks them. The base tag is set to point to the
        // course base in view.html. To restore the references, we use
        // window.location.href to override the base tag href value.
        elmCurrentLink.attr('marker-end',
            'url(' + window.location.href + '#regular)');

        // onMouseOut
        if (opacity == 1) {
          elmCurrentLink.attr('class', 'link');
          // onMouseOver
        } else {
          elmCurrentLink.attr('class', 'link incoming');
        }
        flag = true;
      }

      // shows prerequisites
      if (o.source === dst) {
        // Highlight target/sources of the link
        var elmNodes = graph.selectAll('.' + formatClassName('node', o.target));
        elmNodes.attr('fill-opacity', 1);
        elmNodes.attr('stroke-opacity', 1);
        elmNodes.style('stroke-opacity', 1);
        elmNodes.classed('dimmed', false);

        // Highlight arrows
        var elmCurrentLink = $('path.link[data-source=' + o.source.index + ']');
        elmCurrentLink.attr('data-show', true);
        elmCurrentLink.attr('marker-end',
            'url(' + window.location.href + '#regular)');

        // onMouseOut
        if (opacity == 1) {
          elmCurrentLink.attr('class', 'link');
          // onMouseOver
        } else {
          elmCurrentLink.attr('class', 'link outgoing');
        }

        flag = true;
      }

      if (flag) {
        return 1;
      } else {
        var elmAllLinks = $('path.link:not([data-show])');

        if (opacity == 1) {
          elmAllLinks.attr('marker-end',
              'url(' + window.location.href + '#regular)');
        } else {
          elmAllLinks.attr('marker-end', '');
        }
        return opacity;
      }
    });
  }

  function render() {
    zoom = d3.behavior.zoom();
    zoom.on('zoom', onZoomChanged);

    // Setup layout
    layout = d3.layout
      .force()
      .gravity(.05)
      .charge(-300)
      .linkDistance(100);

    // Setup graph
    graph = d3.select('.graph')
      .append('svg:svg')
      .attr('pointer-events', 'all')
      .call(zoom)
      .append('svg:g')
      .attr('width', graphWidth)
      .attr('height', graphHeight);

    d3.select(window).on("resize", resize);

    // Load graph data
    var graphData = window.getGraphData();
    renderGraph(graphData);

    data = graphData;

    // Resize
    resize();

    centerGraph();

    // Controllers
    $('.control-zoom a').on('click', onControlZoomClicked);
  }

  function resize() {
    graphWidth = window.innerWidth;
    graphHeight = window.innerHeight - 200;
    $('div.graph').height(graphHeight).width(graphWidth - 64);
    graph.attr('width', graphWidth).attr('height', graphHeight);
    layout.size([graphWidth, graphHeight]).resume();
  }

  function centerGraph() {
    var centerTranslate = [
        (graphWidth / 2) - (graphWidth * centerFactor / 2),
        (graphHeight / 2) - (graphHeight * centerFactor / 2)
    ];
    zoom.translate(centerTranslate);

    // render transition
    graph.transition()
      .duration(durationInterval)
      .attr('transform',
        'translate(' +
        zoom.translate() +
        ')' +
        ' scale(' +
        zoom.scale() +
        ')');
  }

  function renderGraph(data) {
    // markers
    graph.append('svg:defs').selectAll('marker')
      .data(['regular'])
      .enter().append('svg:marker')
      .attr('id', String)
      .attr('viewBox', '0 -5 10 10')
      .attr('refX', 15)
      .attr('refY', -1.5)
      .attr('markerWidth', 6)
      .attr('markerHeight', 6)
      .attr('orient', 'auto')
      .append('svg:path')
      .attr('d', 'M0,-5L10,0L0,5');

    // lines
    links = graph.append('svg:g').selectAll("line")
      .data(data.links)
      .enter().append("svg:path")
      .attr('class', 'link')
      .attr("data-target", function (o) {
        return o.target
      })
      .attr('data-source', function (o) {
        return o.source
      })
      .attr('marker-end', function (d) {
        return 'url(' + window.location.href + '#regular)';
      });

    var drag = layout.drag()
        .on("dragstart", dragStart);

    // nodes
    nodes = graph.append('svg:g').selectAll('node')
      .data(data.nodes)
      .enter()
      .append('svg:g')
      .attr('class', 'node')
      .on('mousedown', function() { d3.event.stopPropagation(); })
      .call(drag);

    // circles
    nodes.attr('class', function (d) {
      return formatClassName('node', d)
    });

    nodes.append("svg:circle")
      .attr('class', function (d) {
        return formatClassName('circle', d)
      })
      .attr('r', radius)
      .on('mouseover', _.bind(onNodeMouseOver, this, nodes, links))
      .on('mouseout', _.bind(onNodeMouseOut, this, nodes, links));


    // A copy of the text with a thick white stroke for legibility.
    nodes.append('svg:text')
      .attr('x', 15)
      .attr('y', '.31em')
      .attr('class', function (d) {
        return 'shadow ' + formatClassName('text', d)
      })
      .text(function (d) {
        return d.id;
      });

    nodes.append('svg:text')
      .attr('class', function (d) {
        return formatClassName('text', d)
      })
      .attr('x', 15)
      .attr('y', '.31em')
      .text(function (d) {
        return d.id;
      });

    // build linked index
    data.links.forEach(function (d) {
      linkedByIndex[d.source.index + ',' + d.target.index] = 1;
    });

    // draw the
    layout.nodes(data.nodes);
    layout.links(data.links);
    layout.on('tick', onTick);
    layout.start();

    zoom.scale(0.9);

    // render transition
    graph.transition().duration(durationInterval).attr(
      'transform', 'scale(' + zoom.scale() + ')');
  }

  function onNodeMouseOver(nodes, links, d) {
    // highlight circle
    var elm = findElementByNode('circle', d);
    elm.style('fill', '#b94431');

    // highlight related nodes
    fadeRelatedNodes(d, .05, nodes, links);
  }

  function onNodeMouseOut(nodes, links, d) {
    // highlight circle
    var elm = findElementByNode('circle', d);
    elm.style('fill', '#ccc');

    // highlight related nodes
    fadeRelatedNodes(d, 1, nodes, links);
  }

  function onTick(e) {
    links.attr('d', function (d) {
      var dx = d.target.x - d.source.x,
        dy = d.target.y - d.source.y,
        dr = Math.sqrt(dx * dx + dy * dy);
      return 'M' + d.source.x + ',' + d.source.y + 'A' + dr + ',' + dr +
        ' 0 0,1 ' + d.target.x + ',' + d.target.y;
    });

    nodes.attr('cx', function (d) {
      return d.x;
    }).attr('cy', function (d) {
      return d.y;
    }).attr('transform', function (d) {
      return 'translate(' + d.x + ',' + d.y + ')';
    });
  }

  function onControlZoomClicked(e) {
    var elmTarget = $(this);
    var scaleProcentile = 0.20;

    // scale
    var currentScale = zoom.scale();
    var newScale;
    if (elmTarget.hasClass('control-zoom-in')) {
      newScale = currentScale * (1 + scaleProcentile);
    } else {
      newScale = currentScale * (1 - scaleProcentile);
    }
    newScale = Math.max(newScale, 0);

    // translate
    var centerTranslate = [
        (graphWidth / 2) - (graphWidth * newScale / 2),
        (graphHeight / 2) - (graphHeight * newScale / 2)
    ];

    // store values
    zoom.translate(centerTranslate).scale(newScale);

    // Render transition
    graph.transition().duration(durationInterval).attr('transform',
        'translate(' +
        zoom.translate() +
        ')' +
        ' scale(' +
        zoom.scale() +
        ')');

    // suppress navigating to CB home
    return false;
  }

  function onZoomChanged() {
    graph.attr('transform',
        'translate(' +
        d3.event.translate +
        ')' +
        ' scale(' +
        d3.event.scale +
        ')');
  }

  function dragStart(d) {
    d3.select(this).classed("fixed", d.fixed = true);
  }

  render();
}
