package Printer;

use strict;
use warnings;

use local::lib;
use Text::Xslate qw(mark_raw html_escape);
use Moo;
use namespace::clean;

has 'root_dir' => (
    is       => 'ro',
    required => 1,
);

has 'tpl_path' => (
    is       => 'ro',
    required => 1,
);

has 'ph' => (
    is      => 'ro',
    lazy    => 1,
    default => sub {
        my ($self) = @_;

        return Text::Xslate->new(
            path        => [ $self->root_dir . $self->tpl_path ],
            syntax      => 'TTerse',
            input_layer => ':utf8',
            cache       => 0,
        );
    },
);

our $VERSION = '0.2';

sub do_render {
    my ( $self, %args ) = @_;

    my $h_vars   = $args{vars};
    my $tpl_file = $args{tpl_file};
    my $escape   = $args{escape};

    if ( $escape == 0 ) {
        foreach my $k ( keys %{$h_vars} ) {
            $h_vars->{$k} = mark_raw( $h_vars->{$k} );
        }
    }

    binmode STDOUT, ":encoding(utf-8)";
    return $self->ph->render( $tpl_file, $h_vars )
        || croak( __PACKAGE__ . ' failed to render ' . $tpl_file );
}

1;
